"""Verify the ring SDK layer (app.services.ring) works without a server.

Run: python scripts/test_ring_api.py

For a live E2E check against a running backend, use scripts/sim_ring.py instead.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.ring import (  # noqa: E402
    SensorData,
    SimulatedRing,
    VendorAPIRingSource,
    BLEGATTRingSource,
    parse_hrm,
    uint8,
    uint16_le,
    SCENARIOS,
)


def test_sensor_data_from_dict():
    sd = SensorData.from_dict({"bpm": 85, "stress": 40, "mood": "anxious"})
    assert sd.bpm == 85, f"Expected bpm=85 got {sd.bpm}"
    assert sd.stress == 40, f"Expected stress=40 got {sd.stress}"
    assert sd.mood == "anxious", f"Expected mood=anxious got {sd.mood}"
    assert sd.hrv == 50, "Expected default hrv=50"
    print("OK - SensorData.from_dict")


def test_simulated_determinism():
    r1 = SimulatedRing(username="alaya", scenario="balanced")
    r2 = SimulatedRing(username="alaya", scenario="balanced")
    r1.connect(); r2.connect()
    a, b = r1.read_sensors(), r2.read_sensors()
    assert a.bpm == b.bpm and a.stress == b.stress and a.hrv == b.hrv, "Same user+hour must be deterministic"
    print(f"OK - SimulatedRing deterministic (bpm={a.bpm})")


def test_simulated_scenario_bounds():
    stressed = SimulatedRing(username="stress_demo", scenario="stressed")
    stressed.connect()
    calm = SimulatedRing(username="calm_demo", scenario="calm")
    calm.connect()
    s = stressed.read_sensors()
    c = calm.read_sensors()
    assert 30 <= s.bpm <= 250 and 30 <= c.bpm <= 250, "bpm out of validated range"
    assert s.stress > c.stress, "stressed scenario should exceed calm stress"
    print(f"OK - SimulatedRing scenarios (stressed={s.stress}, calm={c.stress})")


def test_vendor_api_source_with_fetch_fn():
    def fake_fetch():
        return {"bpm": 91, "stress": 55, "spo2": 96.0, "hrv": 40}
    src = VendorAPIRingSource("ring-oura-1", fetch_fn=fake_fetch)
    src.connect()
    sd = src.read_sensors()
    assert sd.bpm == 91, f"Expected bpm=91 got {sd.bpm}"
    assert sd.hrv == 40, f"Expected hrv=40 got {sd.hrv}"
    print("OK - VendorAPIRingSource fetch_fn")


def test_vendor_api_requires_credentials():
    src = VendorAPIRingSource("ring-oura-2")
    try:
        src.connect()
        raise AssertionError("Expected RuntimeError for missing credentials")
    except RuntimeError:
        print("OK - VendorAPIRingSource rejects missing credentials")


def test_unknown_scenario_rejected():
    try:
        SimulatedRing(username="x", scenario="nope")
        raise AssertionError("Expected ValueError for unknown scenario")
    except ValueError:
        print("OK - SimulatedRing rejects unknown scenario")


def test_ble_hrm_parser():
    # Standard HRM: flags=0x00 -> 8-bit bpm in byte 1
    assert parse_hrm(bytes([0x00, 96])) == {"bpm": 96}
    # flags=0x01 -> 16-bit bpm (little-endian) in bytes 1-2
    assert parse_hrm(bytes([0x01, 0x64, 0x00])) == {"bpm": 100}
    assert parse_hrm(b"") == {"bpm": 0}
    print("OK - BLEGATT parse_hrm (8-bit, 16-bit, empty)")


def test_ble_uuid_parsers():
    assert uint8(bytes([42])) == 42
    assert uint16_le(bytes([0x34, 0x12])) == 0x1234
    print("OK - BLEGATT uint8 / uint16_le")


def test_ble_source_requires_bleak():
    src = BLEGATTRingSource(device_id="RING-OEM-001", address="AA:BB:CC:DD:EE:FF")
    try:
        src.connect()
        raise AssertionError("Expected RuntimeError without bleak installed")
    except RuntimeError as e:
        assert "bleak" in str(e)
        print("OK - BLEGATTRingSource guards missing bleak")


if __name__ == "__main__":
    test_sensor_data_from_dict()
    test_simulated_determinism()
    test_simulated_scenario_bounds()
    test_vendor_api_source_with_fetch_fn()
    test_vendor_api_requires_credentials()
    test_unknown_scenario_rejected()
    test_ble_hrm_parser()
    test_ble_uuid_parsers()
    test_ble_source_requires_bleak()
    print(f"\nAll {len(SCENARIOS)} scenarios available: {sorted(SCENARIOS)}")
    print("\nAll ring SDK tests passed!")
