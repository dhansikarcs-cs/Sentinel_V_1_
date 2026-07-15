import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
import bcrypt as _bcrypt

from app.core.config import settings

ALGORITHM = settings.jwt_algorithm
SECRET = settings.jwt_secret


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except JWTError:
        return None


# TODO: swap PBKDF2 for Argon2id once the Samsung SFT funding lands
# ── Encryption (passphrase-derived) ──

_MASTER_KEY: Optional[bytes] = None


def is_encryption_ready() -> bool:
    return _MASTER_KEY is not None


def initialize_encryption(passphrase: str):
    global _MASTER_KEY
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

    hkdf_hmac = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b"sentinel-hmac-key-v1")
    _HMAC_KEY = hkdf_hmac.derive(_MASTER_KEY)


_FERNET: Optional = None
_HMAC_KEY: Optional[bytes] = None


def encrypt_text(plain: str) -> str:
    if not _FERNET or not _MASTER_KEY:
        return plain
    return _FERNET.encrypt(plain.encode()).decode()


def decrypt_text(cipher: str) -> str:
    if not _FERNET or not _MASTER_KEY:
        return cipher
    try:
        return _FERNET.decrypt(cipher.encode()).decode()
    except Exception:
        return "[ACCESS DENIED / DATA CORRUPTED]"


def compute_hmac(data: str) -> str:
    import hmac as hmac_mod
    if not _HMAC_KEY:
        return ""
    return hmac_mod.new(_HMAC_KEY, data.encode(), "sha256").hexdigest()


def verify_hmac(data: str, hmac_val: str) -> bool:
    import hmac as hmac_mod
    if not _HMAC_KEY:
        return False
    expected = compute_hmac(data)
    return hmac_mod.compare_digest(expected, hmac_val)
