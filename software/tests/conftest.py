import os
import sys
import tempfile

# All tests share one temp database to avoid module caching issues
_db_path = tempfile.mktemp(suffix=".db")
os.environ["SENTINEL_DB_PATH"] = _db_path
os.environ["SENTINEL_DB_BACKEND"] = "sqlite"
os.environ["SENTINEL_PASSWORD_SALT"] = "test-salt"

import pytest

# Import patient_profiles_ first so it seeds the DB with proper password hashes
from patient_profiles_ import get_all_patients  # noqa: F401, E402

# Now add test-only profiles (not in the JSON data) for FK references
from database import get_db

with get_db() as db:
    for username in ["unique_test_patient", "charlie_order_test", "nonexistent"]:
        db.execute(
            "INSERT INTO patient_profiles (username, password_hash, name, role) VALUES (?, ?, ?, ?)",
            (username, "test-hash", username.replace("_", " ").title(), "patient")
        )