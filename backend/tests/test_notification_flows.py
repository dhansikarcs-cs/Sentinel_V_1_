import datetime as _dt

import pytest

from app.models.followup import FollowupTask
from app.models.user import User


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def in_reminder_window(monkeypatch):
    class _Fixed:
        @staticmethod
        def now(tz=None):
            real = _dt.datetime.now(_dt.UTC)
            fixed = real.replace(hour=12, minute=0, second=0, microsecond=0)
            return fixed if tz else fixed.replace(tzinfo=None)

    monkeypatch.setattr("app.workers.reminder_worker.datetime", _Fixed)
    yield


def _assign(db_session, patient_username: str, psych_username: str) -> None:
    row = db_session.query(User).filter(User.username == patient_username).first()
    row.assigned_psych = psych_username
    db_session.commit()


def test_journal_create_notifies_assigned_psych(client, make_user, db_session):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient")
    _assign(db_session, patient["username"], psych["username"])

    resp = client.post(
        "/api/journal",
        json={"raw_content": "A quiet, steady kind of day today."},
        headers=_auth(patient["access_token"]),
    )
    assert resp.status_code == 200

    psych_notifs = client.get("/api/notifications", headers=_auth(psych["access_token"])).json()
    match = [n for n in psych_notifs if n["recipient_username"] == psych["username"]]
    assert match, "clinician should receive the journal-submitted notification"
    assert "journal" in match[0]["title"].lower()
    assert match[0]["patient_username"] == patient["username"]

    # the patient must NOT see the clinician-targeted notice
    patient_notifs = client.get("/api/notifications", headers=_auth(patient["access_token"])).json()
    assert all(n["recipient_username"] is None for n in patient_notifs)


def test_journal_without_assigned_psych_creates_no_notice(client, make_user):
    patient = make_user(role="patient")
    client.post(
        "/api/journal",
        json={"raw_content": "Writing without an assigned psychologist today."},
        headers=_auth(patient["access_token"]),
    )
    assert client.get("/api/notifications", headers=_auth(patient["access_token"])).json() == []


def test_followup_grade_update_tracks_timestamp_and_notifies_patient(client, make_user, db_session):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient")
    _assign(db_session, patient["username"], psych["username"])

    created = client.post(
        "/api/followups",
        json={"patient_username": patient["username"], "title": "Breathing exercise"},
        headers=_auth(psych["access_token"]),
    ).json()
    task_id = created["id"]

    # mark done by the patient first
    client.put(
        f"/api/followups/{task_id}",
        json={"status": "completed", "grade": "none"},
        headers=_auth(patient["access_token"]),
    )

    updated = client.put(
        f"/api/followups/{task_id}",
        json={"grade": "green", "feedback": "Great consistency this week."},
        headers=_auth(psych["access_token"]),
    ).json()
    assert updated["grade"] == "green"
    assert updated["grade_updated_at"]
    assert updated["feedback_updated_at"]

    # patient should now have a "Follow-up evaluated" notice
    patient_notifs = client.get("/api/notifications", headers=_auth(patient["access_token"])).json()
    assert any("follow-up" in n["title"].lower() for n in patient_notifs)

    # unchanged re-save does not bump the feedback timestamp
    before = updated["feedback_updated_at"]
    again = client.put(
        f"/api/followups/{task_id}",
        json={"feedback": "Great consistency this week."},
        headers=_auth(psych["access_token"]),
    ).json()
    row2 = db_session.query(FollowupTask).filter(FollowupTask.id == task_id).first()
    assert again["feedback_updated_at"] == before
    assert row2.feedback_updated_at == before


def test_reminder_sweep_creates_at_most_one_per_day(client, make_user, db_session, in_reminder_window):
    from app.workers.reminder_worker import REMINDER_TITLE, _sweep_reminders

    patient = make_user(role="patient")
    assert client.get("/api/notifications", headers=_auth(patient["access_token"])).json() == []

    _sweep_reminders()
    _sweep_reminders()

    notifs = client.get("/api/notifications", headers=_auth(patient["access_token"])).json()
    reminders = [n for n in notifs if n["title"] == REMINDER_TITLE]
    assert len(reminders) == 1

    # patient writes a journal today -> next sweep does not add another reminder
    client.post(
        "/api/journal",
        json={"raw_content": "Took the reminder advice and wrote today."},
        headers=_auth(patient["access_token"]),
    )
    _sweep_reminders()
    notifs = client.get("/api/notifications", headers=_auth(patient["access_token"])).json()
    assert len([n for n in notifs if n["title"] == REMINDER_TITLE]) == 1


def test_reminder_sweep_skips_patients_who_journaled(client, make_user, db_session, in_reminder_window):
    from app.workers.reminder_worker import REMINDER_TITLE, _sweep_reminders

    patient = make_user(role="patient")
    client.post(
        "/api/journal",
        json={"raw_content": "Already journaled during sweep hour."},
        headers=_auth(patient["access_token"]),
    )
    _sweep_reminders()
    notifs = client.get("/api/notifications", headers=_auth(patient["access_token"])).json()
    assert all(n["title"] != REMINDER_TITLE for n in notifs)
