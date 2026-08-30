import uuid

from app.models.ai_analysis import AIAnalysis
from app.models.crisis import CrisisLog, CrisisState
from app.models.emotion_result import EmotionResult
from app.models.journal import JournalEntry
from app.models.risk_assessment import RiskAssessment


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _text() -> str:
    return "Today I felt hopeful about the future and spent time with my family."


def test_patient_creates_journal_and_background_pipeline_runs(client, make_user, db_session):
    user = make_user()
    resp = client.post("/api/journal", json={"raw_content": _text()}, headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    body = resp.json()
    journal_id = body["id"]
    assert body["patient_username"] == user["username"]
    assert body["ai_source"] == "pending"

    entry = db_session.query(JournalEntry).filter(JournalEntry.id == journal_id).first()
    assert entry is not None
    assert entry.summary
    assert entry.ai_source == "rule"
    assert entry.emotions

    assert db_session.query(EmotionResult).filter(EmotionResult.journal_id == journal_id).count() == 1
    assert db_session.query(AIAnalysis).filter(AIAnalysis.journal_id == journal_id).count() == 1
    assert db_session.query(RiskAssessment).filter(RiskAssessment.journal_id == journal_id).count() == 1


def test_empty_journal_rejected(client, make_user):
    user = make_user()
    resp = client.post("/api/journal", json={"raw_content": "   "}, headers=_auth(user["access_token"]))
    assert resp.status_code == 422


def test_sql_injection_content_rejected(client, make_user):
    user = make_user()
    resp = client.post(
        "/api/journal",
        json={"raw_content": "normal text; DROP TABLE patient_profiles; --"},
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 400


def test_xss_content_rejected(client, make_user):
    user = make_user()
    resp = client.post(
        "/api/journal",
        json={"raw_content": "hello <script>alert(1)</script>"},
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 400


def test_idempotent_submission_returns_same_journal(client, make_user, db_session):
    user = make_user()
    key = f"idem-{uuid.uuid4().hex}"
    headers = {**_auth(user["access_token"]), "Idempotency-Key": key}
    first = client.post("/api/journal", json={"raw_content": _text()}, headers=headers)
    second = client.post("/api/journal", json={"raw_content": _text()}, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert db_session.query(JournalEntry).count() == 1


def test_psychologist_can_read_patient_journals_and_summaries(client, make_user):
    patient = make_user(role="patient")
    psych = make_user(role="psychologist")
    client.post("/api/journal", json={"raw_content": _text()}, headers=_auth(patient["access_token"]))

    journals = client.get(f"/api/journal/{patient['username']}", headers=_auth(psych["access_token"]))
    assert journals.status_code == 200
    assert len(journals.json()) == 1

    summaries = client.get(
        f"/api/journal/{patient['username']}/summaries",
        headers=_auth(psych["access_token"]),
    )
    assert summaries.status_code == 200
    assert summaries.json()[0]["summary"]


def test_patient_cannot_read_others_journals(client, make_user):
    a = make_user(role="patient")
    b = make_user(role="patient")
    client.post("/api/journal", json={"raw_content": _text()}, headers=_auth(a["access_token"]))
    resp = client.get(f"/api/journal/{a['username']}", headers=_auth(b["access_token"]))
    assert resp.status_code == 403


def test_delete_journal_is_soft_delete(client, make_user, db_session):
    user = make_user()
    created = client.post("/api/journal", json={"raw_content": _text()}, headers=_auth(user["access_token"]))
    journal_id = created.json()["id"]
    resp = client.delete(f"/api/journal/{journal_id}", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    row = db_session.query(JournalEntry).filter(JournalEntry.id == journal_id).first()
    assert row is not None
    assert row.deleted_at is not None
    assert row.deleted_by == user["username"]


def test_crisis_journal_triggers_crisis_state(client, make_user, db_session):
    user = make_user()
    crisis_text = "I want to die, nobody can help me, end my life"
    client.post("/api/journal", json={"raw_content": crisis_text}, headers=_auth(user["access_token"]))

    state = db_session.query(CrisisState).first()
    assert state is not None
    assert state.active == 1
    assert state.patient_username == user["username"]

    log = db_session.query(CrisisLog).filter(CrisisLog.event == "crisis_auto_triggered").first()
    assert log is not None
    assert log.patient == user["username"]


def test_crisis_rows_are_per_patient(client, make_user, db_session):
    crisis_text = "I want to die, nobody can help me, end my life"
    alice = make_user(username="alice")
    bob = make_user(username="bob")
    client.post("/api/journal", json={"raw_content": crisis_text}, headers=_auth(alice["access_token"]))
    client.post("/api/journal", json={"raw_content": crisis_text}, headers=_auth(bob["access_token"]))

    alice_state = db_session.query(CrisisState).filter(CrisisState.patient_username == "alice").first()
    bob_state = db_session.query(CrisisState).filter(CrisisState.patient_username == "bob").first()
    assert alice_state is not None and bob_state is not None
    assert alice_state.active == 1 and bob_state.active == 1
    assert alice_state.id != bob_state.id


def test_crisis_cooldown_prevents_second_auto_trigger(client, make_user, db_session):
    user = make_user()
    crisis_text = "I want to die, nobody can help me, end my life"
    headers = _auth(user["access_token"])
    first = client.post("/api/journal", json={"raw_content": crisis_text}, headers=headers)
    second = client.post("/api/journal", json={"raw_content": crisis_text + " again"}, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200

    triggers = db_session.query(CrisisLog).filter(CrisisLog.event == "crisis_auto_triggered").count()
    assert triggers == 1

    state = db_session.query(CrisisState).first()
    assert state is not None
    assert state.active == 1

    second_entry = db_session.query(JournalEntry).filter(JournalEntry.id == second.json()["id"]).first()
    assert second_entry is not None
    assert second_entry.summary


def test_resummarize_requires_authorization(client, make_user):
    a = make_user(role="patient")
    b = make_user(role="patient")
    created = client.post("/api/journal", json={"raw_content": _text()}, headers=_auth(a["access_token"]))
    journal_id = created.json()["id"]

    resp = client.post(f"/api/journal/{journal_id}/resummarize", headers=_auth(b["access_token"]))
    assert resp.status_code == 403

    resp = client.post("/api/journal/999999/resummarize", headers=_auth(a["access_token"]))
    assert resp.status_code == 404
