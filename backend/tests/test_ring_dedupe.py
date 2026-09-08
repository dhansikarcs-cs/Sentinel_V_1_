import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.ring import RingSensorLog
from app.models.sensor_reading import SensorReading


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _pair(client, token: str) -> dict:
    resp = client.post(
        "/api/ring/pair",
        json={"serial": f"DEDUPE-{uuid.uuid4().hex[:8]}", "vendor": "test"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    return resp.json()


def _push(client, serial: str, device_token: str, seq=None, bpm=80, **extra) -> object:
    payload = {"bpm": bpm, "stress": 40, "sleep_hours": 7.5, "spo2": 97, "hrv": 55, **extra}
    if seq is not None:
        payload["seq"] = seq
    return client.post(
        "/api/ring/data",
        json=payload,
        headers={"X-Device-Serial": serial, "X-Device-Token": device_token},
    )


def test_idempotent_replay_same_seq_lands_one_row(client, make_user, db_session):
    user = make_user()
    dev = _pair(client, user["access_token"])
    first = _push(client, dev["serial"], dev["token"], seq=7)
    replay = _push(client, dev["serial"], dev["token"], seq=7)
    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json()["id"] == replay.json()["id"]
    assert first.json()["seq"] == 7
    assert db_session.query(RingSensorLog).count() == 1
    assert db_session.query(SensorReading).count() == 1


def test_distinct_seq_inserts_separate_rows(client, make_user, db_session):
    user = make_user()
    dev = _pair(client, user["access_token"])
    _push(client, dev["serial"], dev["token"], seq=1)
    _push(client, dev["serial"], dev["token"], seq=2)
    assert db_session.query(RingSensorLog).count() == 2


def test_legacy_push_without_seq_always_inserts(client, make_user, db_session):
    user = make_user()
    dev = _pair(client, user["access_token"])
    _push(client, dev["serial"], dev["token"])
    _push(client, dev["serial"], dev["token"])
    assert db_session.query(RingSensorLog).count() == 2


def test_dedupe_scoped_to_device(client, make_user, db_session):
    a = make_user()
    b = make_user()
    da = _pair(client, a["access_token"])
    db_ = _pair(client, b["access_token"])
    _push(client, da["serial"], da["token"], seq=3)
    _push(client, db_["serial"], db_["token"], seq=3)
    assert db_session.query(RingSensorLog).count() == 2


def test_raw_json_envelope_stores_seq_at_rest(client, make_user, db_session):
    user = make_user()
    dev = _pair(client, user["access_token"])
    _push(client, dev["serial"], dev["token"], seq=42, bpm=77, timestamp="2026-09-06T10:00:00Z")
    row = db_session.query(RingSensorLog).first()
    assert row.seq == 42
    raw = row.raw_json or ""
    assert '"seq": 42' in str(raw)
    assert '"bpm": 77' in str(raw)
    assert "2026-09-06T10:00:00Z" in str(raw)


def test_unique_index_blocks_duplicate_seq_at_db_level(client, make_user, db_session):
    user = make_user()
    dev = _pair(client, user["access_token"])
    _push(client, dev["serial"], dev["token"], seq=5)
    db_session.rollback()
    dup = RingSensorLog(
        device_id=dev["serial"],
        patient_username=user["username"],
        seq=5,
        bpm=81,
        stress=1,
        sleep_hours=8.0,
        spo2=98.0,
        hrv=60,
        logged_at="x",
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_login_rate_limit_returns_retry_after(client, make_user):
    make_user()
    for _ in range(5):
        resp = client.post("/api/auth/login", json={"username": "nobody", "password": "wrong"})
        assert resp.status_code == 401 or resp.status_code == 429
    locked = client.post("/api/auth/login", json={"username": "nobody", "password": "wrong"})
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0
