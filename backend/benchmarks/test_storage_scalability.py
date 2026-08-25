"""JSON vs SQLite I/O benchmarks — 10/50/100/500 profiles."""

import contextlib
import json
import os
import sys
import tempfile
import threading
import time

from cryptography.fernet import Fernet

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SAMPLE_RECORD = {
    "username": "bench_user",
    "mood_avg": 3.2,
    "stress_level": 42,
    "bpm_avg": 78,
    "hrv_avg": 52,
    "sleep_hours": 6.8,
    "journal_count": 15,
    "crisis_count": 1,
    "last_active": "2026-07-15T10:00:00",
    "risk_score": 2,
}


def generate_profiles(n: int) -> list[dict]:
    """Generate n patient profiles with varying parameters."""
    import random

    profiles = []
    for i in range(n):
        p = dict(SAMPLE_RECORD)
        p["username"] = f"bench_patient_{i:04d}"
        p["mood_avg"] = round(random.uniform(1, 5), 1)
        p["stress_level"] = random.randint(10, 90)
        p["bpm_avg"] = random.randint(60, 130)
        p["hrv_avg"] = random.randint(10, 80)
        p["sleep_hours"] = round(random.uniform(3, 9), 1)
        p["risk_score"] = random.randint(1, 10)
        profiles.append(p)
    return profiles


def _json_io(profiles: list[dict], encrypt: bool) -> dict:
    """Benchmark JSON save/load with optional encryption."""
    key = Fernet.generate_key()
    cipher = Fernet(key)

    tmp = tempfile.mktemp(suffix=".json")
    t0 = time.perf_counter()

    # Write
    data = json.dumps(profiles, indent=2)
    if encrypt:
        data = cipher.encrypt(data.encode()).decode()
    with open(tmp, "w") as f:
        f.write(data)
    write_time = (time.perf_counter() - t0) * 1000

    # Read + decrypt
    t0 = time.perf_counter()
    with open(tmp) as f:
        raw = f.read()
    if encrypt:
        raw = cipher.decrypt(raw.encode()).decode()
    json.loads(raw)
    read_time = (time.perf_counter() - t0) * 1000

    file_size = os.path.getsize(tmp)
    os.remove(tmp)

    return {
        "write_ms": write_time,
        "read_ms": read_time,
        "file_size_bytes": file_size,
    }


def _sqlite_io(profiles: list[dict]) -> dict:
    """Benchmark SQLite write/read via SQLAlchemy."""
    from sqlalchemy import Column, Float, Integer, String, create_engine
    from sqlalchemy.orm import declarative_base, sessionmaker

    tmp = tempfile.mktemp(suffix=".db")
    engine = create_engine(f"sqlite:///{tmp}", connect_args={"check_same_thread": False})
    base = declarative_base()

    class BenchProfile(base):
        __tablename__ = "bench_profiles"
        username = Column(String, primary_key=True)
        mood_avg = Column(Float)
        stress_level = Column(Integer)
        bpm_avg = Column(Integer)
        hrv_avg = Column(Integer)
        sleep_hours = Column(Float)
        journal_count = Column(Integer)
        crisis_count = Column(Integer)
        last_active = Column(String)
        risk_score = Column(Integer)

    base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    # Write
    t0 = time.perf_counter()
    session = session_factory()
    for p in profiles:
        session.add(BenchProfile(**p))
    session.commit()
    session.close()
    write_time = (time.perf_counter() - t0) * 1000

    # Read
    t0 = time.perf_counter()
    session = session_factory()
    rows = session.query(BenchProfile).all()
    [r.__dict__ for r in rows]
    session.close()
    read_time = (time.perf_counter() - t0) * 1000

    engine.dispose()
    file_size = os.path.getsize(tmp)
    with contextlib.suppress(PermissionError):
        os.remove(tmp)

    return {
        "write_ms": write_time,
        "read_ms": read_time,
        "file_size_bytes": file_size,
    }


def run_storage_benchmarks(log_func, quick=False):
    sizes = [10, 50] if quick else [10, 50, 100, 500]

    for n in sizes:
        profiles = generate_profiles(n)

        # Unencrypted JSON
        r = _json_io(profiles, encrypt=False)
        total_ms = r["write_ms"] + r["read_ms"]
        size_kb = r["file_size_bytes"] / 1024
        log_func(
            "JSON Storage (unencrypted)",
            1,
            "N/A",
            f"{n} profiles | {size_kb:.1f}KB",
            total_ms,
            f"{size_kb:.1f}KB",
            True,
            f"write={r['write_ms']:.1f}ms read={r['read_ms']:.1f}ms",
        )

        # Encrypted JSON
        r = _json_io(profiles, encrypt=True)
        total_ms = r["write_ms"] + r["read_ms"]
        size_kb = r["file_size_bytes"] / 1024
        log_func(
            "JSON Storage (encrypted)",
            1,
            "N/A",
            f"{n} profiles | {size_kb:.1f}KB",
            total_ms,
            f"{size_kb:.1f}KB",
            True,
            f"write={r['write_ms']:.1f}ms read={r['read_ms']:.1f}ms overhead={total_ms / (r['write_ms'] + r['read_ms']) * 100:.0f}%",
        )

        # SQLite (current production)
        r = _sqlite_io(profiles)
        total_ms = r["write_ms"] + r["read_ms"]
        size_kb = r["file_size_bytes"] / 1024
        log_func(
            "SQLite Storage",
            1,
            "N/A",
            f"{n} profiles | {size_kb:.1f}KB",
            total_ms,
            f"{size_kb:.1f}KB",
            True,
            f"write={r['write_ms']:.1f}ms read={r['read_ms']:.1f}ms",
        )

    # Concurrency: simulate 10 simultaneous writes
    profiles = generate_profiles(100)
    t0 = time.perf_counter()
    threads = []
    errors = []

    def concurrent_write(profiles_subset):
        try:
            _json_io(profiles_subset, encrypt=False)
        except Exception as e:
            errors.append(str(e))

    for i in range(0, 100, 10):
        t = threading.Thread(target=concurrent_write, args=(profiles[i : i + 10],))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    elapsed = (time.perf_counter() - t0) * 1000

    log_func(
        "JSON Concurrent Writes",
        10,
        "N/A",
        "100 profiles (10 threads x 10 each)",
        elapsed,
        f"{len(errors)} errors",
        len(errors) == 0,
        f"{len(threads)} threads, {elapsed:.1f}ms total",
    )
