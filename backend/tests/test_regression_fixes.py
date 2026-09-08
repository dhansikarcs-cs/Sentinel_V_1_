"""Regression tests for the four audit findings:
1. /api/physio/push must reject physiologically implausible values (bpm=350 etc.).
2. /api/auth/logout must revoke a Bearer-header access token, not just cookies.
3. /api/ml/models/{name} must 404 for unknown models, not 200 + error body.
4. The Ollama AI provider must fail fast (circuit breaker), not stall per request.
"""

import importlib
import time

from app.services import ai_service


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 1. Physio bounds ────────────────────────────────────────────────────────


def test_physio_push_rejects_implausible_bpm(client, make_user):
    user = make_user()
    resp = client.post(
        "/api/physio/push",
        json={"vendor": "simulated", "bpm": 350, "stress": 40, "sleep_hours": 7.0, "spo2": 97, "hrv": 55},
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 422, resp.text
    assert "Heart rate" in resp.json().get("message", str(resp.json()))


def test_physio_push_rejects_negative_hrv(client, make_user):
    user = make_user()
    resp = client.post(
        "/api/physio/push",
        json={"vendor": "simulated", "bpm": 80, "hrv": -40},
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 422, resp.text
    assert "HRV" in resp.json().get("message", str(resp.json()))


def test_physio_push_rejects_out_of_range_spo2(client, make_user):
    user = make_user()
    resp = client.post(
        "/api/physio/push",
        json={"vendor": "simulated", "bpm": 80, "spo2": 45},
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 422, resp.text
    assert "SpO2" in resp.json().get("message", str(resp.json()))


def test_physio_push_still_accepts_clinical_bounds(client, make_user):
    user = make_user()
    resp = client.post(
        "/api/physio/push",
        json={"vendor": "simulated", "bpm": 198, "stress": 99, "sleep_hours": 11.5, "spo2": 99, "hrv": 295},
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 200, resp.text


# ── 2. Logout revokes Bearer token ──────────────────────────────────────────


def test_logout_revokes_bearer_token(client, make_user):
    user = make_user()
    me_before = client.get("/api/patients/me", headers=_auth(user["access_token"]))
    assert me_before.status_code == 200

    resp = client.post("/api/auth/logout", headers=_auth(user["access_token"]))
    assert resp.status_code == 200, resp.text

    me_after = client.get("/api/patients/me", headers=_auth(user["access_token"]))
    assert me_after.status_code == 401, me_after.text


def test_logout_requires_auth(client):
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 401


# ── 3. ML model 404 ─────────────────────────────────────────────────────────


def test_ml_unknown_model_404(client, make_user):
    user = make_user()
    resp = client.get("/api/ml/models/does_not_exist", headers=_auth(user["access_token"]))
    assert resp.status_code == 404, resp.text


def test_ml_known_model_still_200(client, make_user):
    user = make_user()
    resp = client.get("/api/ml/models/emotion_classifier", headers=_auth(user["access_token"]))
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "emotion_classifier"


# ── 4. Ollama circuit breaker ───────────────────────────────────────────────


def test_ollama_circuit_breaker_fails_fast(monkeypatch):
    svc = importlib.reload(ai_service)
    calls = {"n": 0}

    def _boom(url, timeout=0):
        calls["n"] += 1
        raise OSError("connect refused")

    monkeypatch.setattr(svc.urllib.request, "urlopen", _boom)
    svc._ollama_breaker_until = 0.0
    svc._ollama_consecutive_failures = 0

    assert svc._query_ollama("x", prompt_version="regression") is None
    assert calls["n"] == 1
    assert svc._query_ollama("x", prompt_version="regression") is None
    assert calls["n"] == 2

    assert svc._ollama_breaker_until > time.time()
    before = time.time()
    assert svc._query_ollama("x", prompt_version="regression") is None
    assert calls["n"] == 2
    assert time.time() - before < 0.5

    svc._ollama_breaker_until = 0.0
    svc._ollama_consecutive_failures = 0


def test_ollama_success_resets_failure_count(monkeypatch):
    svc = importlib.reload(ai_service)
    states = iter([1, 0])

    def _urlopen(url, timeout=0):
        if next(states):
            raise OSError("boom")

        class _Response:
            def read(self):
                return b'{"response": "hi"}'

        return _Response()

    monkeypatch.setattr(svc.urllib.request, "urlopen", _urlopen)
    svc._ollama_breaker_until = 0.0
    svc._ollama_consecutive_failures = 0

    assert svc._query_ollama("x", prompt_version="regression") is None
    assert svc._query_ollama("x", prompt_version="regression") == "hi"
    assert svc._ollama_consecutive_failures == 0
    assert svc._ollama_breaker_until == 0.0

    svc._ollama_breaker_until = 0.0
    svc._ollama_consecutive_failures = 0
