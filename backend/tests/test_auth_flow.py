import uuid

from app.core.security import decode_access_token

PASSWORD = "Str0ng!Pass1"


def _username(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def test_register_and_login_roundtrip(client, make_user):
    user = make_user()
    assert user["role"] == "patient"
    payload = decode_access_token(user["access_token"])
    assert payload is not None
    assert payload["sub"] == user["username"]
    assert payload["type"] == "access"


def test_register_rejects_weak_password(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": _username("weak"), "password": "password", "name": "W"},
    )
    assert resp.status_code == 422


def test_register_rejects_duplicate_username(client, make_user):
    first = make_user()
    resp = client.post(
        "/api/auth/register",
        json={"username": first["username"], "password": PASSWORD, "name": "Dup"},
    )
    assert resp.status_code == 400
    assert "taken" in resp.json()["message"].lower()


def test_register_rejects_bad_username_chars(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": "bad user!@#", "password": PASSWORD, "name": "Bad"},
    )
    assert resp.status_code == 422


def test_login_wrong_password_rejected(client, make_user):
    user = make_user()
    resp = client.post(
        "/api/auth/login",
        json={"username": user["username"], "password": "Wrong!Pass1"},
    )
    assert resp.status_code == 401


def test_login_unknown_user_rejected(client):
    resp = client.post(
        "/api/auth/login",
        json={"username": _username("ghost"), "password": PASSWORD},
    )
    assert resp.status_code == 401


def test_refresh_rotates_access_token(client, make_user):
    user = make_user()
    assert user["refresh_token"]
    resp = client.post("/api/auth/refresh", json={"refresh_token": user["refresh_token"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] != user["access_token"]
    assert decode_access_token(body["access_token"])["sub"] == user["username"]


def test_refresh_rejects_bogus_token(client):
    resp = client.post("/api/auth/refresh", json={"refresh_token": "not.a.jwt"})
    assert resp.status_code == 401


def test_account_locks_after_repeated_failures(client, make_user):
    user = make_user()
    for _ in range(5):
        resp = client.post(
            "/api/auth/login",
            json={"username": user["username"], "password": "Wrong!Pass1"},
        )
        assert resp.status_code == 401
    resp = client.post(
        "/api/auth/login",
        json={"username": user["username"], "password": PASSWORD},
    )
    assert resp.status_code == 429
    assert "too many" in resp.json()["message"].lower()


def test_role_gating_materializes_psychologist(client, make_user):
    patient = make_user(role="patient")
    psych = make_user(role="psychologist")
    patient_headers = {"Authorization": f"Bearer {patient['access_token']}"}
    psych_headers = {"Authorization": f"Bearer {psych['access_token']}"}

    resp = client.get("/api/journal", headers=patient_headers)
    assert resp.status_code == 200

    resp = client.get(f"/api/journal/{psych['username']}", headers=patient_headers)
    assert resp.status_code == 403

    resp = client.get(f"/api/journal/{patient['username']}", headers=psych_headers)
    assert resp.status_code == 200


def test_protected_route_rejects_missing_token(client):
    resp = client.get("/api/journal")
    assert resp.status_code == 401
