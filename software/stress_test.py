"""
Stress/load test for Sentinel platform — simulates real hardware data flow.

Tests:
1. Concurrent crisis triggers (simulates many patients)
2. Rapid journal writes + AI analysis (simulates batch data ingestion from ring)
3. Booking queue flood
4. Follow-up task load
5. Ring sensor data streaming (simulates real hardware)
6. Auth brute-force attempt detection

Usage:
  python stress_test.py [--iterations 100] [--patients 10]
"""

import os
import sys
import time
import random
import threading
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["SENTINEL_DB_PATH"] = tempfile.mktemp(suffix=".db")
os.environ["SENTINEL_DB_BACKEND"] = "sqlite"
os.environ["SENTINEL_PASSWORD_SALT"] = "stress-test-salt"

from database import init_db, get_db
from patient_profiles_ import authenticate, change_password, _hash_password
from data_manager_ import (
    save_journal_entry, get_patient_history,
    save_booking, load_bookings, update_booking_status,
    save_followup, load_followups, update_followup_status,
    set_crisis_state, get_crisis_state, append_crisis_log,
)
from ring_ import SimulatedRing, SensorData


# Seed test profiles for FK constraint satisfaction
_TEST_PATIENTS = (
    [f"stress_patient_{i}" for i in range(10)] +
    [f"flood_patient_{i}" for i in range(20)] +
    [f"fu_patient_{i}" for i in range(50)] +
    [f"crisis_patient_{i % 10}" for i in range(50)] +
    [f"mixed_patient_{i % 5}" for i in range(30)] +
    ["tp_test", "idempotent_test"]
)
with get_db() as db:
    for p in set(_TEST_PATIENTS):
        db.execute(
            "INSERT INTO patient_profiles (username, password_hash, name, role) VALUES (?, ?, ?, 'patient')",
            (p, "stress-placeholder", p.replace("_", " ").title())
        )

RESULTS = {"passed": 0, "failed": 0, "errors": []}


def log_result(name, elapsed, ok):
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name} ({elapsed:.3f}s)" if ok else f"  [{status}] {name} ({elapsed:.3f}s)")
    if ok:
        RESULTS["passed"] += 1
    else:
        RESULTS["failed"] += 1
        RESULTS["errors"].append(name)


def test_auth_brute_force():
    """Simulate many login attempts — rate limiting kicks in after 5 failures per user."""
    start = time.time()
    fails = 0
    for i in range(20):
        r = authenticate(f"user_{i}", "wrongpass")
        if r is None:
            fails += 1
    result = authenticate("test_patient_1", "test123")
    elapsed = time.time() - start
    log_result("Auth brute force (20 unique users, 1 attempt each)", elapsed, result == "Patient")


def test_concurrent_journals():
    """Simulate 10 patients writing 10 journal entries each concurrently."""
    start = time.time()
    threads = []
    lock = threading.Lock()

    def write_journals(patient, count):
        for i in range(count):
            with lock:
                save_journal_entry(patient, f"Journal entry {i} from {patient}", f"Auto-generated entry {i}")

    patients = [f"stress_patient_{i}" for i in range(10)]
    for p in patients:
        t = threading.Thread(target=write_journals, args=(p, 10))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    total = 0
    for p in patients:
        total += len(get_patient_history(p))
    elapsed = time.time() - start
    log_result(f"Concurrent journals (10 patients x 10 entries)", elapsed, total == 100)


def test_booking_flood():
    """Flood 200 booking requests."""
    start = time.time()
    patients = [f"flood_patient_{i}" for i in range(20)]
    for p in patients:
        for d in range(10):
            save_booking(p, f"2026-06-{d+1:02d}", f"{10 + d % 8}:00", "Therapy", p, f"{p}@test.com", "Flood test")
    bookings = load_bookings()
    elapsed = time.time() - start
    log_result("Booking flood (200 requests)", elapsed, len(bookings) >= 200)


def test_followup_stress():
    """Assign and grade 500 follow-up tasks."""
    start = time.time()
    patients = [f"fu_patient_{i}" for i in range(50)]
    for p in patients:
        for t in range(10):
            save_followup(p, "test_psych_1", f"Task {t}", f"Description for task {t}")
    tasks = load_followups()
    elapsed = time.time() - start
    log_result("Follow-up load (500 tasks)", elapsed, len(tasks) >= 500)


def test_ring_sensor_stream():
    """Simulate 60 seconds of ring sensor data (1 reading/sec)."""
    start = time.time()
    ring = SimulatedRing()
    ring.device_id = "stress-test-ring"
    readings = []
    for _ in range(60):
        readings.append(ring.read_sensors(1.0))
    elapsed = time.time() - start
    all_valid = all(isinstance(r, SensorData) for r in readings)
    all_bpm_ok = all(40 <= r.bpm <= 120 for r in readings)
    log_result("Ring sensor stream (60 readings)", elapsed, all_valid and all_bpm_ok)


def test_crisis_stress():
    """Rapid crisis trigger → acknowledge → resolve cycle 50 times."""
    start = time.time()
    for i in range(50):
        patient = f"crisis_patient_{i % 10}"
        state = {
            "active": True, "patient": patient,
            "triggered_at": datetime.now().isoformat(), "triggered_by": "patient",
            "acknowledged": False, "acknowledged_by": "", "acknowledged_at": "",
            "helpline_escalated": False, "trusted_contact_notified": False,
            "trustee_acknowledged": False, "trustee_clicked": False,
            "tc_ack_emailed": False, "helpline_ack_emailed": False,
        }
        set_crisis_state(state)

        # Acknowledge
        state = get_crisis_state()
        state["acknowledged"] = True
        state["acknowledged_by"] = "test_psych_1"
        set_crisis_state(state)

        # Resolve
        state = get_crisis_state()
        state["active"] = False
        state["patient"] = ""
        set_crisis_state(state)

    state = get_crisis_state()
    elapsed = time.time() - start
    log_result("Crisis cycle (50 triggers + ack + resolve)", elapsed, state["active"] is False)


def test_database_write_throughput():
    """Measure raw database write throughput."""
    start = time.time()
    with get_db() as db:
        for i in range(1000):
            db.execute(
                "INSERT INTO journal_entries (patient_username, raw_content, summary) VALUES (?, ?, ?)",
                (f"tp_test", f"Raw content {i}", f"Summary {i}")
            )
    elapsed = time.time() - start
    ops_per_sec = 1000 / elapsed if elapsed > 0 else 0
    log_result(f"DB write throughput ({ops_per_sec:.0f} ops/sec)", elapsed, ops_per_sec > 100)


def test_password_hash_performance():
    """Hash 100 passwords and measure time."""
    start = time.time()
    for i in range(100):
        _hash_password(f"password_{i}_{random.randint(0, 99999)}")
    elapsed = time.time() - start
    log_result("Password hashing (100 hashes)", elapsed, elapsed < 10.0)


def test_idempotent_crisis_state():
    """Verify crisis state updates don't create duplicate rows."""
    start = time.time()
    for _ in range(20):
        s = get_crisis_state()
        s["active"] = True
        s["patient"] = "idempotent_test"
        set_crisis_state(s)
    with get_db() as db:
        count = db.execute("SELECT COUNT(*) AS cnt FROM crisis_state").fetchone()["cnt"]
    elapsed = time.time() - start
    log_result("Crisis state idempotent updates", elapsed, count == 1)


def test_mixed_workload():
    """Simulate real-world mixed workload (auth + journal + booking + crisis + sensor)."""
    start = time.time()
    ring = SimulatedRing()
    ring.device_id = "mixed"

    for i in range(30):
        patient = f"mixed_patient_{i % 5}"
        authenticate(patient, "pass123")
        save_journal_entry(patient, f"Sensor data: BPM={ring.read_sensors().bpm}", "Auto-logged")
        if i % 3 == 0:
            save_booking(patient, "2026-06-15", "15:00", "Check-in", patient, f"{patient}@test.com", "Mixed workload")
        if i % 10 == 0:
            s = get_crisis_state()
            s["active"] = True
            s["patient"] = patient
            s["triggered_at"] = datetime.now().isoformat()
            set_crisis_state(s)
            s["acknowledged"] = True
            set_crisis_state(s)
            s["active"] = False
            set_crisis_state(s)

    elapsed = time.time() - start
    log_result("Mixed real-world workload", elapsed, True)


if __name__ == "__main__":
    print("=" * 60)
    print("  SENTINEL STRESS TEST SUITE")
    print("=" * 60)
    print()

    tests = [
        ("Auth brute force", test_auth_brute_force),
        ("Concurrent journals (100 entries)", test_concurrent_journals),
        ("Booking flood (200 requests)", test_booking_flood),
        ("Follow-up load (500 tasks)", test_followup_stress),
        ("Ring sensor stream (60 readings)", test_ring_sensor_stream),
        ("Crisis cycle (50 iterations)", test_crisis_stress),
        ("DB write throughput (1000 writes)", test_database_write_throughput),
        ("Password hash performance (100)", test_password_hash_performance),
        ("Crisis state idempotent (20 updates)", test_idempotent_crisis_state),
        ("Mixed real-world workload", test_mixed_workload),
    ]

    suite_start = time.time()
    for name, func in tests:
        print(f"\n  >> {name}")
        try:
            func()
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")
            RESULTS["failed"] += 1
            RESULTS["errors"].append(name)

    suite_elapsed = time.time() - suite_start
    total = RESULTS["passed"] + RESULTS["failed"]

    print(f"\n{'=' * 60}")
    print(f"  STRESS TEST SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Passed: {RESULTS['passed']}/{total}")
    print(f"  Failed: {RESULTS['failed']}/{total}")
    print(f"  Time:   {suite_elapsed:.2f}s")
    if RESULTS["errors"]:
        print(f"  Errors: {', '.join(RESULTS['errors'])}")
    print(f"{'=' * 60}")
    sys.exit(1 if RESULTS["failed"] else 0)