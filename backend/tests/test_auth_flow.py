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
        json={"username": _username("weak"), "password": "password", "name": "W Plus", "dob": "2006-05-14", "occupation": "Student"},
    )
    assert resp.status_code == 422
    assert "uppercase" in resp.json()["message"]


def test_register_rejects_duplicate_username(client, make_user):
    first = make_user()
    resp = client.post(
        "/api/auth/register",
        json={"username": first["username"], "password": PASSWORD, "name": "Dup User", "dob": "2006-05-14", "occupation": "Student"},
    )
    assert resp.status_code == 400
    assert "taken" in resp.json()["message"].lower()


def test_register_rejects_bad_username_chars(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": "bad user!@#", "password": PASSWORD, "name": "Bad"},
    )
    assert resp.status_code == 422


def test_register_psychologist_requires_valid_professional_code(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": _username("dr"), "password": PASSWORD, "name": "Dr Test", "role": "psychologist", "professional_code": "NOT-A-CODE", "dob": "1986-03-21", "occupation": "Trauma"},
    )
    assert resp.status_code == 400


def test_register_psychologist_with_valid_codes(client):
    username = _username("dr")
    resp = client.post(
        "/api/auth/register",
        json={"username": username, "password": PASSWORD, "name": "Dr Test", "role": "psychologist", "professional_code": "PSY-0001", "dob": "1986-03-21", "occupation": "Trauma specialist"},
    )
    assert resp.status_code == 200
    login = client.post(
        "/api/auth/login",
        json={"username": username, "password": PASSWORD},
    )
    assert login.status_code == 200
    assert login.json()["role"] == "Psychologist"
    me = client.get("/api/patients/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["data"]["role"] == "psychologist"
    assert me.json()["data"]["clinic"] == "SENTINEL-01"
    assert me.json()["data"]["professional_code"] == "PSY-0001"
    assert me.json()["data"]["occupation"] == "Trauma specialist"


def test_professional_code_derives_clinic(client):
    username = _username("dr")
    resp = client.post(
        "/api/auth/register",
        json={"username": username, "password": PASSWORD, "name": "Dr", "role": "psychologist", "professional_code": "PSY-0004", "dob": "1986-03-21", "occupation": "Trauma"},
    )
    assert resp.status_code == 200
    login = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    me = client.get("/api/patients/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert me.json()["data"]["clinic"] == "SENTINEL-04"


def test_professional_code_unique_per_psychologist(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": _username("dr"), "password": PASSWORD, "name": "Dr One", "role": "psychologist", "professional_code": "PSY-0002", "dob": "1986-03-21", "occupation": "Anxiety"},
    )
    assert resp.status_code == 200
    dup = client.post(
        "/api/auth/register",
        json={"username": _username("dr"), "password": PASSWORD, "name": "Dr Two", "role": "psychologist", "professional_code": "PSY-0002", "dob": "1986-03-21", "occupation": "Anxiety"},
    )
    assert dup.status_code == 400


def test_register_patient_occupation_is_free_text(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": _username("p"), "password": PASSWORD, "name": "P R", "occupation": "Engineer", "dob": "1997-11-02"},
    )
    assert resp.status_code == 200


def test_register_rejects_numeric_name(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": _username("p"), "password": PASSWORD, "name": "12345", "dob": "2006-05-14", "occupation": "Student"},
    )
    assert resp.status_code == 422


def test_register_rejects_missing_occupation(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": _username("p"), "password": PASSWORD, "name": "Test User", "dob": "2006-05-14"},
    )
    assert resp.status_code == 422


def test_register_rejects_future_dob(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": _username("p"), "password": PASSWORD, "name": "Test User", "dob": "3080-01-01", "occupation": "Student"},
    )
    assert resp.status_code == 422


def test_patient_psychologist_must_match_clinic(client):
    dr = _username("dr")
    assert client.post(
        "/api/auth/register",
        json={"username": dr, "password": PASSWORD, "name": "Dr", "role": "psychologist", "professional_code": "PSY-0003", "dob": "1986-03-21", "occupation": "Trauma"},
    ).status_code == 200
    bad = client.post(
        "/api/auth/register",
        json={"username": _username("p"), "password": PASSWORD, "name": "P R", "role": "patient", "clinic_code": "SENTINEL-05", "occupation": "Engineer", "assigned_psych": dr, "dob": "1997-11-02"},
    )
    assert bad.status_code == 400
    assert "clinic" in bad.json()["message"].lower()
    good = client.post(
        "/api/auth/register",
        json={"username": _username("p"), "password": PASSWORD, "name": "P R", "role": "patient", "clinic_code": "SENTINEL-03", "occupation": "Engineer", "assigned_psych": dr, "dob": "1997-11-02"},
    )
    assert good.status_code == 200


def test_login_wrong_password_rejected(client, make_user):
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
