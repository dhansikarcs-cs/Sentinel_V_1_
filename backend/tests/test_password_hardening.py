"""Password hardening tests: Argon2id hashing, bcrypt fallback, decrypt hard-fail."""

import bcrypt
import pytest

from app.core import security
from app.core.security import EncryptionNotReadyError, hash_password, password_needs_rehash, verify_password


def test_argon2_hash_verifies():
    hashed = hash_password("correct horse battery staple")
    assert hashed.startswith("$argon2id$")
    assert verify_password("correct horse battery staple", hashed)
    assert not password_needs_rehash(hashed)


def test_argon2_wrong_password_rejected():
    hashed = hash_password("right")
    assert not verify_password("wrong", hashed)


def test_legacy_bcrypt_hash_still_verifies():
    legacy = bcrypt.hashpw(b"old-pass", bcrypt.gensalt()).decode()
    assert verify_password("old-pass", legacy)
    assert password_needs_rehash(legacy)  # flagged for transparent upgrade


def test_empty_or_garbage_hash_rejected():
    assert not verify_password("anything", "")
    assert not verify_password("anything", "not-a-hash")
    assert password_needs_rehash("not-a-hash")


def test_decrypt_refuses_when_encryption_required_and_not_ready(monkeypatch):
    monkeypatch.setattr(security, "_FERNET", None)
    monkeypatch.setattr(security, "_MASTER_KEY", None)
    monkeypatch.setattr(security.settings, "encryption_required", True)
    with pytest.raises(EncryptionNotReadyError):
        security.decrypt_text("some-ciphertext")


def test_decrypt_allowed_when_not_required(monkeypatch):
    monkeypatch.setattr(security, "_FERNET", None)
    monkeypatch.setattr(security, "_MASTER_KEY", None)
    monkeypatch.setattr(security.settings, "encryption_required", False)
    assert security.decrypt_text("cipher") == "cipher"
