import uuid

from app.models.ring import RingSensorLog
from app.models.sensor_reading import SensorReading


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _pair(client, token: str) -> dict:
    resp = client.post(
        "/api/ring/pair",
        json={"serial": f"SENT-{uuid.uuid4().hex[:8]}", "vendor": "test"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    return resp.json()


def _push(client, serial: str, device_token: str, **overrides) -> dict:
    payload = {"bpm": 80, "stress": 40, "sleep_hours": 7.5, "spo2": 97, "hrv": 55, **overrides}
    return client.post(
        "/api/ring/data",
        json=payload,
        headers={"X-Device-Serial": serial, "X-Device-Token": device_token},
    )


def test_pair_then_device_push_roundtrip(client, make_user, db_session):
    user = make_user()
    device = _pair(client, user["access_token"])
    assert device["status"] == "paired"
    assert device["token"]

    resp = _push(client, device["serial"], device["token"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["patient_username"] == user["username"]
    assert body["bpm"] == 80

    assert db_session.query(RingSensorLog).count() == 1
    assert db_session.query(SensorReading).count() == 1


def test_device_push_rejects_wrong_token(client, make_user):
    user = make_user()
    device = _pair(client, user["access_token"])
    resp = _push(client, device["serial"], "wrong-token")
    assert resp.status_code == 401


def test_device_push_rejects_unknown_serial(client, make_user):
    make_user()
    resp = client.post(
        "/api/ring/data",
        json={"bpm": 80},
        headers={"X-Device-Serial": "NOPE-123", "X-Device-Token": "anything"},
    )
    assert resp.status_code == 401


def test_patient_jwt_fallback_push(client, make_user):
    user = make_user()
    resp = client.post("/api/ring/data", json={"bpm": 88, "stress": 20}, headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["bpm"] == 88


def test_push_rejects_out_of_range_values(client, make_user):
    user = make_user()
    resp = client.post("/api/ring/data", json={"bpm": 999}, headers=_auth(user["access_token"]))
    assert resp.status_code == 422


def test_unpair_revokes_device_token(client, make_user):
    user = make_user()
    device = _pair(client, user["access_token"])

    resp = client.post(f"/api/ring/unpair?serial={device['serial']}", headers=_auth(user["access_token"]))
    assert resp.status_code == 200

    resp = _push(client, device["serial"], device["token"])
    assert resp.status_code == 401


def test_pair_serial_conflict(client, make_user):
    user = make_user()
    device = _pair(client, user["access_token"])
    resp = client.post(
        "/api/ring/pair",
        json={"serial": device["serial"], "vendor": "test"},
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 409


def test_unpair_forbidden_for_other_patient(client, make_user):
    a = make_user()
    b = make_user()
    device = _pair(client, a["access_token"])
    resp = client.post(f"/api/ring/unpair?serial={device['serial']}", headers=_auth(b["access_token"]))
    assert resp.status_code == 403


def test_psychologist_can_list_all_devices(client, make_user):
    a = make_user()
    psych = make_user(role="psychologist")
    _pair(client, a["access_token"])
    resp = client.get("/api/ring/devices", headers=_auth(psych["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
