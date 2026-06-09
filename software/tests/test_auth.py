import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from patient_profiles_ import authenticate, change_password, get_patient_name, get_psychologist_name, get_all_patients


class TestAuth:
    def test_authenticate_valid_patient(self):
        role = authenticate("test_patient_1", "test123")
        assert role == "Patient", f"Expected Patient, got {role}"

    def test_authenticate_valid_psychologist(self):
        role = authenticate("test_psych_1", "doc123")
        assert role == "Psychologist", f"Expected Psychologist, got {role}"

    def test_authenticate_invalid_password(self):
        role = authenticate("test_patient_1", "wrongpass")
        assert role is None

    def test_authenticate_invalid_user(self):
        role = authenticate("nonexistent", "test123")
        assert role is None

    def test_change_password(self):
        assert change_password("test_patient_1", "test123", "newpass456") is True
        assert authenticate("test_patient_1", "test123") is None
        assert authenticate("test_patient_1", "newpass456") == "Patient"

    def test_get_patient_name(self):
        assert get_patient_name("test_patient_1") == "Noah Smith"

    def test_get_psychologist_name(self):
        assert get_psychologist_name("test_psych_1") == "Dr. Sophia Davis"

    def test_get_unknown_patient(self):
        assert get_patient_name("unknown") == "unknown"

    def test_get_all_patients(self):
        patients = get_all_patients()
        assert "test_patient_1" in patients
        assert "test_patient_10" in patients
        assert "test_psych_1" not in patients

    def test_password_hashing_different(self):
        from patient_profiles_ import _hash_password
        h1 = _hash_password("test123")
        h2 = _hash_password("test456")
        assert h1 != h2

    def test_password_hash_consistent(self):
        from patient_profiles_ import _hash_password
        h1 = _hash_password("testpass")
        h2 = _hash_password("testpass")
        assert h1 == h2


if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
