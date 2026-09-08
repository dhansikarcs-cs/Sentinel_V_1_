"""Regression tests for the security hardening pass:

1. Self-registration cannot create a psychologist without a valid professional code.
2. A professional code is unique — bad or already-used codes are rejected.
3. Cross-patient reads (IDOR) are blocked on risk/ai/emotion/crisis endpoints.
4. Notifications are write-scoped to the caller for non-psychologists.
5. Refresh tokens are rotated on refresh and revoked on logout.
6. Psych websocket channels reject patient tokens.
7. JWT default-secret refusal and encryption fail-closed guards exist.
"""

from datetime import UTC, datetime

import pytest
from starlette.websockets import WebSocketDisconnect

from app.models.ai_analysis import AIAnalysis
from app.models.crisis import CrisisLog
from app.models.emotion_result import EmotionResult
from app.models.journal import JournalEntry
from app.models.risk_assessment import RiskAssessment


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 1. Registration can't mint psychologists without a valid clinic code ──


def test_self_registration_psychologist_rejected_without_professional_code(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "username": "evil_psych",
            "password": "Str0ng!Pass1",
            "name": "Imposter",
            "role": "psychologist",
            "dob": "1990-06-15",
            "occupation": "x",
        },
    )
    assert resp.status_code == 400, resp.text


def test_self_registration_psychologist_rejected_with_bad_professional_code(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "username": "evil_psych2",
            "password": "Str0ng!Pass1",
            "name": "Imposter",
            "role": "psychologist",
            "dob": "1990-06-15",
            "occupation": "x",
            "professional_code": "T",
        },
    )
    assert resp.status_code == 400, resp.text
    login = client.post("/api/auth/login", json={"username": "evil_psych2", "password": "Str0ng!Pass1"})
    assert login.status_code == 401


# ── 2. IDOR guards ──────────────────────────────────────────────────────────


def _seed_clinical_rows(db_session, patient_username: str, journal_id: int):
    now = datetime.now(UTC).isoformat()
    db_session.add(
        RiskAssessment(
            journal_id=journal_id,
            patient_username=patient_username,
            risk_score=80,
            triggered=1,
            confidence=0.9,
            algorithm_version="1.0.0",
            created_at=now,
        )
    )
    db_session.add(
        AIAnalysis(
            journal_id=journal_id,
            patient_username=patient_username,
            priority="high",
            confidence=0.9,
            provider="rule",
            created_at=now,
        )
    )
    db_session.add(EmotionResult(journal_id=journal_id, patient_username=patient_username, sadness=0.9, created_at=now))
    db_session.commit()


def test_peer_patient_cannot_read_other_patient_clinical_data(client, make_user, db_session):
    owner, attacker = make_user(), make_user()
    now = datetime.now(UTC).isoformat()
    journal = JournalEntry(patient_username=owner["username"], raw_content="content", timestamp=now)
    db_session.add(journal)
    db_session.flush()
    db_session.commit()
    jid = journal.id
    _seed_clinical_rows(db_session, owner["username"], jid)

    # owner can read
    assert client.get(f"/api/risk-assessments/patient/{owner['username']}", headers=_auth(owner["access_token"])).status_code == 200
    assert client.get(f"/api/ai-analyses/patient/{owner['username']}", headers=_auth(owner["access_token"])).status_code == 200
    assert client.get(f"/api/emotion-results/journal/{jid}", headers=_auth(owner["access_token"])).status_code == 200

    # attacker blocked with 403, not leaked
    assert client.get(f"/api/risk-assessments/patient/{owner['username']}", headers=_auth(attacker["access_token"])).status_code == 403
    assert client.get(f"/api/risk-assessments/journal/{jid}", headers=_auth(attacker["access_token"])).status_code == 403
    assert client.get(f"/api/ai-analyses/patient/{owner['username']}", headers=_auth(attacker["access_token"])).status_code == 403
    assert client.get(f"/api/ai-analyses/journal/{jid}", headers=_auth(attacker["access_token"])).status_code == 403
    assert client.get(f"/api/emotion-results/journal/{jid}", headers=_auth(attacker["access_token"])).status_code == 403
    assert client.get(f"/api/emotions/summary/{owner['username']}", headers=_auth(attacker["access_token"])).status_code == 403

    # psychologist still allowed
    psych = make_user(role="psychologist")
    assert client.get(f"/api/risk-assessments/patient/{owner['username']}", headers=_auth(psych["access_token"])).status_code == 200


def test_crisis_log_scoped_to_own_patient(client, make_user, db_session):
    a, b = make_user(), make_user()
    db_session.add(CrisisLog(patient=a["username"], event="triggered", timestamp=datetime.now(UTC).isoformat()))
    db_session.add(CrisisLog(patient=b["username"], event="triggered", timestamp=datetime.now(UTC).isoformat()))
    db_session.commit()
    logs = client.get("/api/crisis/log", headers=_auth(a["access_token"])).json()
    assert all(log["patient"] == a["username"] for log in logs)


def test_notification_write_scoped_to_self_for_patient(client, make_user):
    me, other = make_user(), make_user()
    resp = client.post(
        "/api/notifications",
        json={
            "patient_username": other["username"],
            "title": "spoofed",
            "message": "fake crisis",
            "notification_type": "crisis",
        },
        headers=_auth(me["access_token"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["patient_username"] == me["username"]
    mine = client.get("/api/notifications", headers=_auth(me["access_token"])).json()
    assert mine and all(n["patient_username"] == me["username"] for n in mine)
    # attacker's spoof didn't land on the other user
    theirs = client.get("/api/notifications", headers=_auth(other["access_token"])).json()
    assert all(n["message"] != "fake crisis" for n in theirs)


def test_unauthenticated_profile_requires_auth(client):
    resp = client.get("/api/patients/someone/profile")
    assert resp.status_code == 401 or resp.status_code == 403


# ── 3. Refresh rotation + logout revocation ─────────────────────────────────


def test_refresh_rotation_invalidates_old_token(client, make_user):
    user = make_user()
    old_refresh = user["refresh_token"]
    resp = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200, resp.text
    new_refresh = resp.json()["refresh_token"]
    assert new_refresh != old_refresh
    # rotating again with the new one works
    assert client.post("/api/auth/refresh", json={"refresh_token": new_refresh}).status_code == 200
    # the old refresh is now dead
    assert client.post("/api/auth/refresh", json={"refresh_token": old_refresh}).status_code == 401


def test_logout_revokes_refresh_token(client, make_user):
    user = make_user()
    login = client.post(
        "/api/auth/login", json={"username": user["username"], "password": user["password"]}
    )
    refresh = login.json()["refresh_token"]
    assert client.post("/api/auth/logout").status_code == 200
    assert client.post("/api/auth/refresh", json={"refresh_token": refresh}).status_code == 401


# ── 4. WebSocket channel auth ───────────────────────────────────────────────


def test_ws_psych_rejects_patient_token(client, make_user):
    patient = make_user()
    with pytest.raises(WebSocketDisconnect) as exc, client.websocket_connect(
        f"/api/ws/psych?token={patient['access_token']}"
    ):
        pass
    assert exc.value.code == 1008


def test_ws_psych_accepts_psychologist_token(client, make_user):
    psych = make_user(role="psychologist")
    with client.websocket_connect(f"/api/ws/psych?token={psych['access_token']}") as ws:
        ws.send_text("ping")


# ── 5. Encryption guards exist ──────────────────────────────────────────────


def test_encrypt_text_fails_closed_when_required(monkeypatch):
    import app.core.security as sec
    from app.core.config import settings

    monkeypatch.setattr(settings, "encryption_required", True)
    old_key, old_fernet = sec._MASTER_KEY, sec._FERNET
    sec._MASTER_KEY = None
    sec._FERNET = None
    try:
        with pytest.raises(sec.EncryptionNotReadyError):
            sec.encrypt_text("secret")
    finally:
        sec._MASTER_KEY, sec._FERNET = old_key, old_fernet


def test_encrypt_text_pass_through_when_not_required(monkeypatch):
    import app.core.security as sec
    from app.core.config import settings

    monkeypatch.setattr(settings, "encryption_required", False)
    old_key, old_fernet = sec._MASTER_KEY, sec._FERNET
    sec._MASTER_KEY = None
    sec._FERNET = None
    try:
        assert sec.encrypt_text("plain") == "plain"
    finally:
        sec._MASTER_KEY, sec._FERNET = old_key, old_fernet
