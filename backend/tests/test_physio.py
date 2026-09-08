"""Tests for the device-agnostic physiological ingestion layer."""

from app.models.physiological_signal import PhysiologicalSignal
from app.models.ring import RingSensorLog
from app.models.sensor_reading import SensorReading
from app.services.physio import (
    adapt_oura,
    adapt_samsung,
    adapt_simulated,
    normalize_payload,
)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Normalization service ───────────────────────────────────────────────────


def test_normalize_simulated_payload():
    r = normalize_payload("simulated", {"bpm": 80, "stress": 40, "sleep_hours": 7.5, "spo2": 97, "hrv": 55})
    assert r.heart_rate == 80
    assert r.stress == 40
    assert r.sleep_hours == 7.5
    assert r.hrv_rmssd == 55
    assert r.quality == "simulated"


def test_normalize_oura_payload():
    r = normalize_payload(
        "oura",
        {
            "heart_rate": {"bpm": 72},
            "spo2": {"percentage": 96.5},
            "sleep": {"total_sleep_duration_hours": 6.8},
            "hrv": {"instantaneous": [42]},
            "temperature": 36.4,
        },
    )
    assert r.heart_rate == 72
    assert r.spo2 == 96.5
    assert r.sleep_hours == 6.8
    assert r.hrv_rmssd == 42.0
    assert r.temperature == 36.4


def test_normalize_samsung_payload():
    r = normalize_payload(
        "samsung",
        {
            "heart_rate": {"heartRate": 66},
            "stress": {"level": 30},
            "sleep": {"sleepDurationHours": 7.2},
            "bodyTemperature": 36.6,
        },
    )
    assert r.heart_rate == 66
    assert r.stress == 30
    assert r.sleep_hours == 7.2
    assert r.temperature == 36.6


def test_normalize_unknown_vendor_falls_back_to_generic():
    r = normalize_payload("some_future_wearable", {"heart_rate": 88, "hrv_rmssd": 33})
    assert r.heart_rate == 88
    assert r.hrv_rmssd == 33.0


def test_normalize_missing_fields_default_to_zero():
    r = normalize_payload("generic", {})
    assert r.heart_rate == 0
    assert r.hrv_rmssd == 0.0
    assert r.quality == "unknown"


def test_adapters_are_callable():
    # Guard against adapter signature drift
    for fn in (adapt_simulated, adapt_oura, adapt_samsung):
        result = fn({})
        assert hasattr(result, "heart_rate")


# ── Endpoint ────────────────────────────────────────────────────────────────


def test_push_physio_simulated_roundtrip(client, make_user, db_session):
    user = make_user()
    resp = client.post(
        "/api/physio/push",
        json={"vendor": "simulated", "bpm": 90, "stress": 55, "sleep_hours": 6.5, "spo2": 97, "hrv": 60},
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["vendor"] == "simulated"
    assert body["heart_rate"] == 90
    assert body["stress"] == 55

    # Stored in the common schema
    assert db_session.query(PhysiologicalSignal).count() == 1
    # And mirrored to legacy tables for the risk engine
    assert db_session.query(RingSensorLog).count() == 1
    assert db_session.query(SensorReading).count() == 1


def test_push_physio_oura_normalizes(client, make_user, db_session):
    user = make_user()
    resp = client.post(
        "/api/physio/push",
        json={
            "vendor": "oura",
            "heart_rate": {"bpm": 74},
            "spo2": {"percentage": 96},
            "sleep": {"total_sleep_duration_hours": 7.1},
            "hrv": {"instantaneous": [48]},
        },
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["heart_rate"] == 74
    assert body["hrv_rmssd"] == 48.0
    assert body["sleep_hours"] == 7.1
    assert body["respiratory_rate"] == 0

    row = db_session.query(PhysiologicalSignal).first()
    assert row.vendor == "oura"


def test_push_physio_samsung_normalizes(client, make_user):
    user = make_user()
    resp = client.post(
        "/api/physio/push",
        json={
            "vendor": "samsung",
            "heart_rate": {"heartRate": 68},
            "stress": {"level": 25},
            "sleep": {"sleepDurationHours": 7.4},
        },
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["heart_rate"] == 68
    assert body["stress"] == 25
    assert body["sleep_hours"] == 7.4


def test_list_own_signals(client, make_user):
    user = make_user()
    client.post(
        "/api/physio/push",
        json={"vendor": "simulated", "bpm": 80, "stress": 40, "sleep_hours": 7.0, "spo2": 97, "hrv": 50},
        headers=_auth(user["access_token"]),
    )
    client.post(
        "/api/physio/push",
        json={"vendor": "oura", "heart_rate": {"bpm": 75}, "hrv": {"instantaneous": [44]}},
        headers=_auth(user["access_token"]),
    )
    resp = client.get("/api/physio/signals", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    vendors = {s["vendor"] for s in resp.json()}
    assert vendors == {"simulated", "oura"}


def test_patient_does_not_see_other_patient_signals(client, make_user):
    a = make_user()
    b = make_user()
    client.post(
        "/api/physio/push",
        json={"vendor": "simulated", "bpm": 80, "stress": 40, "sleep_hours": 7.0, "spo2": 97, "hrv": 50},
        headers=_auth(a["access_token"]),
    )
    resp = client.get("/api/physio/signals", headers=_auth(b["access_token"]))
    assert resp.status_code == 200
    assert resp.json() == []


def test_psychologist_can_view_patient_signals(client, make_user):
    patient = make_user()
    psych = make_user(role="psychologist")
    client.post(
        "/api/physio/push",
        json={"vendor": "simulated", "bpm": 82, "stress": 45, "sleep_hours": 6.8, "spo2": 96, "hrv": 52},
        headers=_auth(patient["access_token"]),
    )
    resp = client.get(
        f"/api/physio/patient/{patient['username']}",
        headers=_auth(psych["access_token"]),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_vendors_listing(client, make_user):
    user = make_user()
    client.post(
        "/api/physio/push",
        json={"vendor": "simulated", "bpm": 80, "stress": 40, "sleep_hours": 7.0, "spo2": 97, "hrv": 50},
        headers=_auth(user["access_token"]),
    )
    resp = client.get("/api/physio/vendors", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert "simulated" in resp.json()["vendors"]
