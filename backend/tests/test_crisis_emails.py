from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.models.crisis import CrisisState
from app.models.user import User


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _set_patient(db_session, username, trusted_contact="", assigned_psych=""):
    db_session.query(User).filter(User.username == username).update(
        {"trusted_contact": trusted_contact, "assigned_psych": assigned_psych}
    )
    db_session.commit()


def test_notify_emails_trusted_contact_and_psychologist(client, make_user, db_session, monkeypatch):
    captured = []
    monkeypatch.setattr(
        "app.api.crisis.send_email",
        lambda to, subject, body: (captured.append((to, subject)) or True),
    )
    psych = make_user(role="psychologist")
    patient = make_user(role="patient")
    db_session.query(User).filter(User.username == psych["username"]).update(
        {"contact_info": "psych@example.com"}
    )
    _set_patient(db_session, patient["username"], "mom@example.com", psych["username"])

    h = auth_headers(patient["access_token"])
    assert client.post("/api/crisis/trigger", headers=h).status_code == 200
    resp = client.post("/api/crisis/notify-trusted-contact", headers=h)
    assert resp.status_code == 200

    tos = {to for to, _ in captured}
    assert "mom@example.com" in tos
    assert "psych@example.com" in tos
    data = resp.json()["data"]
    assert data["email_sent"] is True
    assert data["psych_email_sent"] is True


def test_notify_without_trusted_contact_still_emails_psychologist(client, make_user, db_session, monkeypatch):
    captured = []
    monkeypatch.setattr(
        "app.api.crisis.send_email",
        lambda to, subject, body: (captured.append((to, subject)) or True),
    )
    psych = make_user(role="psychologist")
    patient = make_user(role="patient")
    db_session.query(User).filter(User.username == psych["username"]).update(
        {"contact_info": "psych@example.com"}
    )
    _set_patient(db_session, patient["username"], "", psych["username"])

    h = auth_headers(patient["access_token"])
    assert client.post("/api/crisis/trigger", headers=h).status_code == 200
    resp = client.post("/api/crisis/notify-trusted-contact", headers=h)
    assert resp.status_code == 200

    tos = {to for to, _ in captured}
    assert "psych@example.com" in tos
    assert "mom@example.com" not in tos
    assert resp.json()["data"]["email_sent"] is False
    assert resp.json()["data"]["psych_email_sent"] is True


def test_auto_escalation_emails_trusted_contact_and_psychologist(client, make_user, db_session, monkeypatch):
    captured = []
    monkeypatch.setattr(
        "app.api.crisis.send_email",
        lambda to, subject, body: (captured.append((to, subject)) or True),
    )
    psych = make_user(role="psychologist")
    patient = make_user(role="patient")
    db_session.query(User).filter(User.username == psych["username"]).update(
        {"contact_info": "psych@example.com"}
    )
    _set_patient(db_session, patient["username"], "mom@example.com", psych["username"])

    h = auth_headers(patient["access_token"])
    assert client.post("/api/crisis/trigger", headers=h).status_code == 200
    db_session.query(CrisisState).filter(CrisisState.patient_username == patient["username"]).update(
        {"triggered_at": (datetime.now(UTC) - timedelta(seconds=35)).isoformat()}
    )
    db_session.commit()

    assert client.get("/api/crisis/elapsed", headers=h).status_code == 200
    tos = {to for to, _ in captured}
    assert "mom@example.com" in tos
    assert "psych@example.com" in tos


def test_contact_update_rejects_phone_for_trusted_contact(client, make_user):
    patient = make_user(role="patient")
    h = auth_headers(patient["access_token"])

    ok = client.put("/api/patients/me/contact", json={"contact_info": "5551234", "trusted_contact": "mom@example.com"}, headers=h)
    assert ok.status_code == 200

    bad = client.put("/api/patients/me/contact", json={"contact_info": "", "trusted_contact": "just-a-phone-number"}, headers=h)
    assert bad.status_code == 400


def test_contact_update_rejects_phone_for_psychologist_email(client, make_user):
    psych = make_user(role="psychologist")
    h = auth_headers(psych["access_token"])

    bad = client.put("/api/patients/me/contact", json={"contact_info": "5551234", "trusted_contact": ""}, headers=h)
    assert bad.status_code == 400

    ok = client.put("/api/patients/me/contact", json={"contact_info": "psych@example.com", "trusted_contact": ""}, headers=h)
    assert ok.status_code == 200


def test_get_me_exposes_psych_email_and_helpline_email(client, make_user, db_session, monkeypatch):
    monkeypatch.setattr(settings, "crisis_helpline_email", "help@example.com")
    psych = make_user(role="psychologist")
    patient = make_user(role="patient")
    db_session.query(User).filter(User.username == psych["username"]).update(
        {"contact_info": "psych@example.com"}
    )
    _set_patient(db_session, patient["username"], "mom@example.com", psych["username"])

    me = client.get("/api/patients/me", headers=auth_headers(patient["access_token"])).json()["data"]
    assert me["psych_email"] == "psych@example.com"
    assert me["helpline_email"] == "help@example.com"
