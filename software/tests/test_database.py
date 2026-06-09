import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_db


class TestDatabase:
    def test_init_db(self):
        with get_db() as db:
            tables = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            names = [r["name"] for r in tables]
            required = [
                "patient_profiles", "journal_entries", "clinical_notes",
                "bookings", "crisis_state", "crisis_log", "followups",
                "ring_sessions", "ring_sensor_log",
            ]
            for t in required:
                assert t in names, f"Missing table: {t}"

    def test_insert_and_query(self):
        with get_db() as db:
            db.execute(
                "INSERT INTO patient_profiles (username, password_hash, name, role) VALUES (?, ?, ?, ?)",
                ("test_user", "abc123", "Test User", "patient")
            )
            row = db.execute(
                "SELECT username, name, role FROM patient_profiles WHERE username = ?",
                ("test_user",)
            ).fetchone()
            assert row["username"] == "test_user"
            assert row["name"] == "Test User"
            assert row["role"] == "patient"

    def test_journal_crud(self):
        with get_db() as db:
            db.execute(
                "INSERT INTO journal_entries (patient_username, raw_content, summary) VALUES (?, ?, ?)",
                ("unique_test_patient", "Feeling good today", "Positive mood")
            )
            rows = db.execute(
                "SELECT * FROM journal_entries WHERE patient_username = ?", ("unique_test_patient",)
            ).fetchall()
            assert len(rows) == 1
            assert rows[0]["summary"] == "Positive mood"

    def test_crisis_state(self):
        with get_db() as db:
            db.execute(
                "INSERT INTO crisis_state (active, patient_username) VALUES (?, ?)",
                (1, "test_patient_1")
            )
            row = db.execute("SELECT * FROM crisis_state ORDER BY id DESC LIMIT 1").fetchone()
            assert row["active"] == 1
            assert row["patient_username"] == "test_patient_1"

    def test_followups(self):
        import uuid
        fid = str(uuid.uuid4())[:8]
        with get_db() as db:
            db.execute(
                "INSERT INTO followups (id, patient_username, psychologist_username, title) VALUES (?, ?, ?, ?)",
                (fid, "test_patient_1", "test_psych_1", "Breathing exercise")
            )
            row = db.execute("SELECT * FROM followups WHERE id = ?", (fid,)).fetchone()
            assert row["title"] == "Breathing exercise"
            assert row["status"] == "pending"

    def test_ring_sensor_log(self):
        with get_db() as db:
            db.execute("INSERT INTO ring_sessions (patient_username) VALUES (?)", ("test_patient_1",))
            sid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.execute(
                "INSERT INTO ring_sensor_log (session_id, bpm, stress) VALUES (?, ?, ?)",
                (sid, 75, 30)
            )
            row = db.execute("SELECT * FROM ring_sensor_log WHERE session_id = ?", (sid,)).fetchone()
            assert row["bpm"] == 75
            assert row["stress"] == 30


if __name__ == "__main__":
    pytest.main([__file__])
