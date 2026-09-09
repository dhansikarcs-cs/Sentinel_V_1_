import os
from datetime import UTC, datetime, timedelta
from typing import Optional

import bcrypt as _bcrypt
from argon2 import PasswordHasher
from argon2 import exceptions as argon2_exceptions
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = settings.jwt_algorithm
SECRET = settings.jwt_secret

_argon2 = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)

_BCRYPT_PREFIX = b"$2"


def hash_password(password: str) -> str:
    return _argon2.hash(password)


def _is_bcrypt(hashed: str) -> bool:
    return hashed.encode().startswith(_BCRYPT_PREFIX)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against an Argon2id (preferred) or legacy bcrypt hash."""
    if not hashed:
        return False
    if _is_bcrypt(hashed):
        try:
            return _bcrypt.checkpw(plain.encode(), hashed.encode())
        except Exception:
            return False
    try:
        _argon2.verify(hashed, plain)
        return True
    except (argon2_exceptions.VerifyMismatchError, argon2_exceptions.InvalidHashError, ValueError):
        return False


def password_needs_rehash(hashed: str) -> bool:
    """True for legacy bcrypt hashes (and malformed values) that should be
    transparently re-hashed with Argon2id on the next successful login."""
    if not hashed or _is_bcrypt(hashed):
        return True
    try:
        return _argon2.check_needs_rehash(hashed)
    except argon2_exceptions.InvalidHashError:
        return True


REFRESH_SECRET = SECRET + ":refresh"
REFRESH_EXPIRE_DAYS = 30


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    now_ts = int(datetime.now(UTC).timestamp())
    import uuid as _uuid

    to_encode.update(
        {
            "exp": expire,
            "iat": now_ts,
            "iss": "sentinel-health",
            "jti": _uuid.uuid4().hex[:16],
            "type": "access",
        }
    )
    return jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)


def create_refresh_token(username: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=REFRESH_EXPIRE_DAYS)
    now_ts = int(datetime.now(UTC).timestamp())
    import uuid as _uuid

    payload = {
        "sub": username,
        "exp": expire,
        "iat": now_ts,
        "iss": "sentinel-health",
        "jti": _uuid.uuid4().hex[:16],
        "type": "refresh",
    }
    return jwt.encode(payload, REFRESH_SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, REFRESH_SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


# ── Encryption (passphrase-derived; Argon2id-ready, Fernet AEAD for integrity) ──

_MASTER_KEY: bytes | None = None


def is_encryption_ready() -> bool:
    return _MASTER_KEY is not None


def initialize_encryption(passphrase: str):
    global _MASTER_KEY, _FERNET
    import base64

    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    salt_hex = os.environ.get("SENTINEL_ENCRYPTION_SALT") or settings.encryption_salt
    if not salt_hex:
        salt = os.urandom(16)
        salt_hex = salt.hex()
        os.environ["SENTINEL_ENCRYPTION_SALT"] = salt_hex
    else:
        salt = bytes.fromhex(salt_hex)

    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600000)
    _MASTER_KEY = kdf.derive(passphrase.encode())

    from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand

    hkdf = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b"sentinel-fernet-key-v1")
    fernet_key = base64.urlsafe_b64encode(hkdf.derive(_MASTER_KEY))
    _FERNET = Fernet(fernet_key)


_FERNET: Optional = None


class EncryptionNotReadyError(RuntimeError):
    """Raised when an encrypted write is attempted before the master key is set."""


def _encryption_required() -> bool:
    return getattr(settings, "encryption_required", True)


def encrypt_text(plain: str) -> str:
    if not _FERNET or not _MASTER_KEY:
        if _encryption_required():
            raise EncryptionNotReadyError(
                "Encryption not initialized — refusing to write plaintext. "
                "Call POST /api/auth/unlock or set SENTINEL_ENCRYPTION_PASSPHRASE."
            )
        import logging

        logging.getLogger("sentinel.security").warning(
            "Writing unencrypted data: encryption not initialized (encryption_required=false)"
        )
        return plain
    return _FERNET.encrypt(plain.encode()).decode()


def decrypt_text(cipher: str) -> str:
    if not _FERNET or not _MASTER_KEY:
        if _encryption_required():
            raise EncryptionNotReadyError(
                "Encryption not initialized — refusing to decrypt. "
                "Call POST /api/auth/unlock or set SENTINEL_ENCRYPTION_PASSPHRASE."
            )
        return cipher
    try:
        return _FERNET.decrypt(cipher.encode()).decode()
    except Exception:
        return "[ACCESS DENIED / DATA CORRUPTED]"
