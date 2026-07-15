import os
import json
import hmac
import hashlib
from datetime import datetime
from contextlib import contextmanager

_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(_ROOT, "..", "data")

# ── Backend Selection ─────────────────────────────────────

BACKEND = os.getenv("SENTINEL_DB_BACKEND", "sqlite").lower()


class _CursorWrapper:
    """Unified cursor wrapper: SQLite uses conn.execute(), PostgreSQL uses cursor."""
    def __init__(self, conn):
        self._conn = conn
        self._cur = None

    def execute(self, sql, params=None):
        if BACKEND == "postgres":
            sql = sql.replace("?", "%s")
            self._cur = self._conn.cursor()
            self._cur.execute(sql, params or ())
        else:
            self._cur = self._conn.execute(sql, params or [])
        return self._cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if BACKEND == "postgres" and self._cur:
            self._cur.close()
        self._conn.close()


# ── Encrypted Security Module ─────────────────────────────
#
# 1. MASTER PASSPHRASE (typed at startup, NEVER stored on disk)
#    │
#    ▼ PBKDF2HMAC(iter=600k, salt=global_salt)
#    master_key (32 bytes, RAM only)
#    │
#    ├── HKDF(info="fernet")  → key_fernet (base64) → Fernet(AES-128-CBC + HMAC)
#    ├── HKDF(info="hmac")    → key_hmac  (32 raw)  → HMAC-SHA256 signing
#    └── HKDF(info="pii:USER", salt=user_salt)       → per-user PII encryption key
#
# 2. KEY SEPARATION: Fernet key ≠ HMAC key (two derivation paths from same master)
# 3. PER-USER SALTS: os.urandom(16) per profile, stored in patient_profiles.encryption_salt
# 4. PII ENCRYPTED: contact_info, trusted_contact encrypted with per-user key
# 5. FAILURES CAUGHT: InvalidToken logged, clean "ACCESS DENIED" returned

import base64
import secrets

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
SECURITY_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "security_audit.log")


def _load_env():
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def _log_security_event(event: str):
    try:
        os.makedirs(os.path.dirname(SECURITY_LOG) or ".", exist_ok=True)
        with open(SECURITY_LOG, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] {event}\n")
    except Exception:
        pass


# ── Module-level state (never serialised to disk) ────────

_fernet_key: bytes | None = None       # base64-encoded 32-byte Fernet key
_hmac_key: bytes | None = None          # raw 32-byte HMAC key
_master_key: bytes | None = None        # raw 32-byte master key (PBKDF2 output)
_encryption_ready: bool = False


def is_encryption_ready() -> bool:
    return _encryption_ready


def _derive_keys(master_key: bytes):
    """Derive Fernet key and HMAC key from master key using HKDF."""
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    global _fernet_key, _hmac_key
    raw_fernet = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None,
        info=b"sentinel-fernet-key-v1",
    ).derive(master_key)
    _fernet_key = base64.urlsafe_b64encode(raw_fernet)
    _hmac_key = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None,
        info=b"sentinel-hmac-key-v1",
    ).derive(master_key)


def _derive_pii_key(master_key: bytes, username: str, user_salt: bytes) -> bytes:
    """Derive a per-user PII encryption key from the master key + user salt + username."""
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=user_salt,
        info=f"sentinel-pii-key-{username}".encode(),
    ).derive(master_key)


def _get_global_salt() -> bytes:
    """Return the stored global PBKDF2 salt.  Auto-generate once if missing."""
    _load_env()
    stored = os.environ.get("SENTINEL_ENCRYPTION_SALT")
    if stored:
        try:
            return bytes.fromhex(stored)
        except Exception:
            pass
    new_salt = secrets.token_bytes(16)
    hex_salt = new_salt.hex()
    os.environ["SENTINEL_ENCRYPTION_SALT"] = hex_salt
    os.makedirs(os.path.dirname(ENV_FILE) or ".", exist_ok=True)
    # Remove old key lines but keep salt
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                if not line.strip().startswith("SENTINEL_ENCRYPTION_KEY"):
                    lines.append(line)
    with open(ENV_FILE, "w") as f:
        for line in lines:
            f.write(line)
        f.write(f"\nSENTINEL_ENCRYPTION_SALT={hex_salt}\n")
    return new_salt


def _migrate_old_encrypted_data():
    """Migrate data encrypted with old .env-stored key to new passphrase-derived key.

    Also encrypts any plaintext PII (contact_info, trusted_contact) using per-user keys.
    """
    _load_env()
    old_key_b64 = os.environ.get("SENTINEL_ENCRYPTION_KEY")
    has_old_key = bool(old_key_b64)
    old_fernet = None
    if has_old_key:
        try:
            from cryptography.fernet import Fernet
            old_fernet = Fernet(old_key_b64.encode())
        except Exception:
            has_old_key = False

    _log_security_event("Starting encryption migration")
    migrated = 0
    try:
        with get_db() as db:
            # 1. Migrate journal entries from old key
            if has_old_key and old_fernet:
                rows = db.execute("SELECT id, raw_content FROM journal_entries WHERE raw_content != ''").fetchall()
                for r in rows:
                    cipher = r["raw_content"]
                    if cipher.startswith("gAAAAA"):
                        try:
                            plain = old_fernet.decrypt(cipher.encode()).decode()
                            new_cipher = encrypt_text(plain)
                            db.execute("UPDATE journal_entries SET raw_content = ? WHERE id = ?", (new_cipher, r["id"]))
                            migrated += 1
                        except Exception:
                            pass

            # 2. Migrate clinical notes from old key
            if has_old_key and old_fernet:
                rows2 = db.execute("SELECT id, raw_notes FROM clinical_notes WHERE raw_notes != ''").fetchall()
                for r in rows2:
                    cipher = r["raw_notes"]
                    if cipher.startswith("gAAAAA"):
                        try:
                            plain = old_fernet.decrypt(cipher.encode()).decode()
                            new_cipher = encrypt_text(plain)
                            db.execute("UPDATE clinical_notes SET raw_notes = ? WHERE id = ?", (new_cipher, r["id"]))
                            migrated += 1
                        except Exception:
                            pass

            # 3. Encrypt plaintext PII using per-user keys
            pii_migrated = 0
            users = db.execute("SELECT username, contact_info, trusted_contact, psych_trusted_contact FROM patient_profiles").fetchall()
            for u in users:
                uname = u["username"]
                changes = {}
                for field in ("contact_info", "trusted_contact", "psych_trusted_contact"):
                    val = u[field] or ""
                    if val and not val.startswith("gAAAAA"):
                        changes[field] = encrypt_pii(val, uname)
                if changes:
                    salt_exists = db.execute("SELECT encryption_salt FROM patient_profiles WHERE username = ?", (uname,)).fetchone()
                    if salt_exists and not salt_exists["encryption_salt"]:
                        db.execute("UPDATE patient_profiles SET encryption_salt = ? WHERE username = ?",
                                   (secrets.token_bytes(16).hex(), uname))
                    for field, enc_val in changes.items():
                        db.execute(f"UPDATE patient_profiles SET {field} = ? WHERE username = ?", (enc_val, uname))
                        pii_migrated += 1

        # Remove old key from .env
        lines = []
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE) as f:
                for line in f:
                    if not line.strip().startswith("SENTINEL_ENCRYPTION_KEY"):
                        lines.append(line)
            with open(ENV_FILE, "w") as f:
                for line in lines:
                    f.write(line)
        _log_security_event(f"Migration complete: {migrated} records re-encrypted (old key), {pii_migrated} PII fields encrypted. Old key removed.")
    except Exception as e:
        _log_security_event(f"Migration error: {e}")


def initialize_encryption(master_passphrase: str):
    """Initialise the in-memory encryption keys from a master passphrase.

    Must be called once at app startup after the user (clinic admin / psychologist)
    types the passphrase.  The passphrase never touches disk; only a non-secret
    PBKDF2 salt is stored in .env.
    """
    global _master_key, _encryption_ready

    if _encryption_ready:
        return

    salt = _get_global_salt()
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,
    )
    _master_key = kdf.derive(master_passphrase.encode())
    _derive_keys(_master_key)
    _encryption_ready = True

    _migrate_old_encrypted_data()
    _log_security_event("Encryption initialised from passphrase (RAM only)")


def encrypt_text(plain: str) -> str:
    if not plain or not _encryption_ready:
        return plain
    from cryptography.fernet import Fernet
    f = Fernet(_fernet_key)
    return f.encrypt(plain.encode()).decode()


def decrypt_text(cipher: str) -> str:
    if not cipher or not _encryption_ready:
        return cipher
    from cryptography.fernet import Fernet
    from cryptography.fernet import InvalidToken
    try:
        f = Fernet(_fernet_key)
        return f.decrypt(cipher.encode()).decode()
    except InvalidToken:
        _log_security_event(f"InvalidToken on decrypt — possible tampered data")
        return "[ACCESS DENIED / DATA CORRUPTED]"
    except Exception:
        _log_security_event(f"Decryption exception (non-token)")
        return "[ACCESS DENIED / DATA CORRUPTED]"


def compute_hmac(data: str) -> str:
    if not _encryption_ready:
        return ""
    return hmac.new(_hmac_key, data.encode(), hashlib.sha256).hexdigest()


def verify_hmac(data: str, expected_hmac: str) -> bool:
    if not _encryption_ready:
        return True
    return hmac.compare_digest(compute_hmac(data), expected_hmac)


# ── Per-user PII encryption ────────────────────────────

def get_user_encryption_salt(username: str) -> bytes | None:
    """Retrieve or initialise the per-user encryption salt from patient_profiles."""
    try:
        with get_db() as db:
            row = db.execute(
                "SELECT encryption_salt FROM patient_profiles WHERE username = ?", (username,)
            ).fetchone()
            if row and row["encryption_salt"]:
                return bytes.fromhex(row["encryption_salt"])
    except Exception:
        pass
    return None


def set_user_encryption_salt(username: str, salt: bytes):
    """Store a per-user encryption salt hex in patient_profiles."""
    try:
        with get_db() as db:
            db.execute(
                "UPDATE patient_profiles SET encryption_salt = ? WHERE username = ?",
                (salt.hex(), username)
            )
    except Exception:
        pass


def _ensure_user_salt(username: str) -> bytes:
    """Return existing user salt or create a new one."""
    salt = get_user_encryption_salt(username)
    if salt is None:
        salt = secrets.token_bytes(16)
        set_user_encryption_salt(username, salt)
    return salt


def encrypt_pii(plain: str, username: str) -> str:
    """Encrypt PII (contact_info, trusted_contact) using a per-user derived key."""
    if not plain or not _encryption_ready or not _master_key:
        return plain
    user_salt = _ensure_user_salt(username)
    key = _derive_pii_key(_master_key, username, user_salt)
    from cryptography.fernet import Fernet
    f = Fernet(base64.urlsafe_b64encode(key))
    return f.encrypt(plain.encode()).decode()


def decrypt_pii(cipher: str, username: str) -> str:
    """Decrypt PII using the per-user derived key."""
    if not cipher or not _encryption_ready or not _master_key:
        return cipher
    user_salt = get_user_encryption_salt(username)
    if user_salt is None:
        return cipher
    from cryptography.fernet import Fernet
    from cryptography.fernet import InvalidToken
    try:
        key = _derive_pii_key(_master_key, username, user_salt)
        f = Fernet(base64.urlsafe_b64encode(key))
        return f.decrypt(cipher.encode()).decode()
    except InvalidToken:
        _log_security_event(f"InvalidToken on PII decrypt for user '{username}'")
        return "[ACCESS DENIED / DATA CORRUPTED]"
    except Exception:
        return "[ACCESS DENIED / DATA CORRUPTED]"


# ── Schema ─────────────────────────────────────────────────

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS patient_profiles (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'patient',
    age INTEGER DEFAULT 0,
    occupation TEXT DEFAULT '',
    clinic_code TEXT DEFAULT '',
    trusted_contact TEXT DEFAULT '',
    locked_until TEXT DEFAULT '',
    failed_attempts INTEGER DEFAULT 0,
    assigned_psych TEXT DEFAULT '',
    onboarding_step INTEGER DEFAULT 0,
    contact_info TEXT DEFAULT '',
    psych_trusted_contact TEXT DEFAULT '',
    encryption_salt TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clinic_codes (
    code TEXT PRIMARY KEY,
    used INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS profession_codes (
    code TEXT PRIMARY KEY,
    used INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_username TEXT NOT NULL,
    raw_content TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    hmac TEXT DEFAULT '',
    ai_source TEXT DEFAULT '',
    emotions TEXT DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_username) REFERENCES patient_profiles(username)
);

CREATE TABLE IF NOT EXISTS clinical_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    psychologist_username TEXT NOT NULL,
    patient_username TEXT NOT NULL,
    raw_notes TEXT DEFAULT '',
    ai_synthesis TEXT DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (psychologist_username) REFERENCES patient_profiles(username),
    FOREIGN KEY (patient_username) REFERENCES patient_profiles(username)
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_username TEXT NOT NULL,
    psychologist_username TEXT DEFAULT '',
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    session_type TEXT DEFAULT '',
    members TEXT DEFAULT '',
    contact TEXT DEFAULT '',
    explanation TEXT DEFAULT '',
    status TEXT DEFAULT 'Pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_username) REFERENCES patient_profiles(username)
);

CREATE TABLE IF NOT EXISTS psych_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    psychologist_username TEXT NOT NULL,
    date TEXT NOT NULL,
    start_time TEXT DEFAULT '09:00',
    end_time TEXT DEFAULT '17:00',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(psychologist_username, date)
);

CREATE TABLE IF NOT EXISTS crisis_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    active INTEGER DEFAULT 0,
    patient_username TEXT DEFAULT '',
    triggered_at TEXT DEFAULT '',
    triggered_by TEXT DEFAULT '',
    acknowledged INTEGER DEFAULT 0,
    acknowledged_by TEXT DEFAULT '',
    acknowledged_at TEXT DEFAULT '',
    helpline_escalated INTEGER DEFAULT 0,
    trusted_contact_notified INTEGER DEFAULT 0,
    trustee_acknowledged INTEGER DEFAULT 0,
    trustee_clicked INTEGER DEFAULT 0,
    tc_ack_emailed INTEGER DEFAULT 0,
    helpline_ack_emailed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS crisis_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event TEXT NOT NULL,
    patient_username TEXT DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT '',
    details TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS followups (
    id TEXT PRIMARY KEY,
    patient_username TEXT NOT NULL,
    psychologist_username TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    file_path TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    proof_file TEXT DEFAULT '',
    grade TEXT DEFAULT 'none',
    feedback TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_username) REFERENCES patient_profiles(username),
    FOREIGN KEY (psychologist_username) REFERENCES patient_profiles(username)
);

CREATE TABLE IF NOT EXISTS ring_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_username TEXT NOT NULL,
    device_id TEXT DEFAULT '',
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    ended_at TEXT DEFAULT '',
    session_data TEXT DEFAULT '[]',
    FOREIGN KEY (patient_username) REFERENCES patient_profiles(username)
);

CREATE TABLE IF NOT EXISTS ring_sensor_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    bpm INTEGER DEFAULT 0,
    stress INTEGER DEFAULT 0,
    sleep REAL DEFAULT 0.0,
    spo2 REAL DEFAULT 0.0,
    mood TEXT DEFAULT '',
    accel_x REAL DEFAULT 0.0,
    accel_y REAL DEFAULT 0.0,
    accel_z REAL DEFAULT 0.0,
    temp REAL DEFAULT 0.0,
    FOREIGN KEY (session_id) REFERENCES ring_sessions(id)
);

CREATE TABLE IF NOT EXISTS auth_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    event TEXT NOT NULL,
    ip_address TEXT DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT DEFAULT '',
    detail TEXT DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mood_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_username TEXT NOT NULL,
    date TEXT NOT NULL,
    emoji TEXT NOT NULL,
    label TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_username) REFERENCES patient_profiles(username)
);
"""

SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS patient_profiles (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'patient',
    age INTEGER DEFAULT 0,
    occupation TEXT DEFAULT '',
    clinic_code TEXT DEFAULT '',
    trusted_contact TEXT DEFAULT '',
    locked_until TEXT DEFAULT '',
    failed_attempts INTEGER DEFAULT 0,
    assigned_psych TEXT DEFAULT '',
    onboarding_step INTEGER DEFAULT 0,
    contact_info TEXT DEFAULT '',
    psych_trusted_contact TEXT DEFAULT '',
    encryption_salt TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS clinic_codes (
    code TEXT PRIMARY KEY,
    used INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS profession_codes (
    code TEXT PRIMARY KEY,
    used INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS journal_entries (
    id SERIAL PRIMARY KEY,
    patient_username TEXT NOT NULL REFERENCES patient_profiles(username),
    raw_content TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    hmac TEXT DEFAULT '',
    ai_source TEXT DEFAULT '',
    emotions TEXT DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS clinical_notes (
    id SERIAL PRIMARY KEY,
    psychologist_username TEXT NOT NULL REFERENCES patient_profiles(username),
    patient_username TEXT NOT NULL REFERENCES patient_profiles(username),
    raw_notes TEXT DEFAULT '',
    ai_synthesis TEXT DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    patient_username TEXT NOT NULL REFERENCES patient_profiles(username),
    psychologist_username TEXT DEFAULT '',
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    session_type TEXT DEFAULT '',
    members TEXT DEFAULT '',
    contact TEXT DEFAULT '',
    explanation TEXT DEFAULT '',
    status TEXT DEFAULT 'Pending',
    created_at TEXT NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS psych_availability (
    id SERIAL PRIMARY KEY,
    psychologist_username TEXT NOT NULL,
    date TEXT NOT NULL,
    start_time TEXT DEFAULT '09:00',
    end_time TEXT DEFAULT '17:00',
    created_at TEXT NOT NULL DEFAULT NOW(),
    UNIQUE(psychologist_username, date)
);

CREATE TABLE IF NOT EXISTS crisis_state (
    id SERIAL PRIMARY KEY,
    active INTEGER DEFAULT 0,
    patient_username TEXT DEFAULT '',
    triggered_at TEXT DEFAULT '',
    triggered_by TEXT DEFAULT '',
    acknowledged INTEGER DEFAULT 0,
    acknowledged_by TEXT DEFAULT '',
    acknowledged_at TEXT DEFAULT '',
    helpline_escalated INTEGER DEFAULT 0,
    trusted_contact_notified INTEGER DEFAULT 0,
    trustee_acknowledged INTEGER DEFAULT 0,
    trustee_clicked INTEGER DEFAULT 0,
    tc_ack_emailed INTEGER DEFAULT 0,
    helpline_ack_emailed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS crisis_log (
    id SERIAL PRIMARY KEY,
    event TEXT NOT NULL,
    patient_username TEXT DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT NOW(),
    source TEXT DEFAULT '',
    details TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS followups (
    id TEXT PRIMARY KEY,
    patient_username TEXT NOT NULL REFERENCES patient_profiles(username),
    psychologist_username TEXT NOT NULL REFERENCES patient_profiles(username),
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    file_path TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    proof_file TEXT DEFAULT '',
    grade TEXT DEFAULT 'none',
    feedback TEXT DEFAULT '',
    created_at TEXT DEFAULT NOW(),
    updated_at TEXT DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ring_sessions (
    id SERIAL PRIMARY KEY,
    patient_username TEXT NOT NULL REFERENCES patient_profiles(username),
    device_id TEXT DEFAULT '',
    started_at TEXT DEFAULT NOW(),
    ended_at TEXT DEFAULT '',
    session_data TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS ring_sensor_log (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES ring_sessions(id),
    timestamp TEXT NOT NULL DEFAULT NOW(),
    bpm INTEGER DEFAULT 0,
    stress INTEGER DEFAULT 0,
    sleep REAL DEFAULT 0.0,
    spo2 REAL DEFAULT 0.0,
    mood TEXT DEFAULT '',
    accel_x REAL DEFAULT 0.0,
    accel_y REAL DEFAULT 0.0,
    accel_z REAL DEFAULT 0.0,
    temp REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS auth_log (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    event TEXT NOT NULL,
    ip_address TEXT DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS activity_log (
    id SERIAL PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT DEFAULT '',
    detail TEXT DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mood_log (
    id SERIAL PRIMARY KEY,
    patient_username TEXT NOT NULL,
    date TEXT NOT NULL,
    emoji TEXT NOT NULL,
    label TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT NOW()
);

"""

_MIGRATIONS_PG = [
    "ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS locked_until TEXT DEFAULT ''",
    "ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS failed_attempts INTEGER DEFAULT 0",
    "ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS age INTEGER DEFAULT 0",
    "ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS occupation TEXT DEFAULT ''",
    "ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS clinic_code TEXT DEFAULT ''",
    "ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS hmac TEXT DEFAULT ''",
    "ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS ai_source TEXT DEFAULT ''",
    "ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS emotions TEXT DEFAULT ''",
    "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS psychologist_username TEXT DEFAULT ''",
    "ALTER TABLE profession_codes DROP COLUMN IF EXISTS assigned_to",
    "ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS assigned_psych TEXT DEFAULT ''",
    "ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS onboarding_step INTEGER DEFAULT 0",
    "ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS contact_info TEXT DEFAULT ''",
    "ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS psych_trusted_contact TEXT DEFAULT ''",
    "ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS encryption_salt TEXT DEFAULT ''",
]

_MIGRATIONS_SQLITE = [
    "ALTER TABLE patient_profiles ADD COLUMN locked_until TEXT DEFAULT ''",
    "ALTER TABLE patient_profiles ADD COLUMN failed_attempts INTEGER DEFAULT 0",
    "ALTER TABLE patient_profiles ADD COLUMN age INTEGER DEFAULT 0",
    "ALTER TABLE patient_profiles ADD COLUMN occupation TEXT DEFAULT ''",
    "ALTER TABLE patient_profiles ADD COLUMN clinic_code TEXT DEFAULT ''",
    "ALTER TABLE journal_entries ADD COLUMN hmac TEXT DEFAULT ''",
    "ALTER TABLE journal_entries ADD COLUMN ai_source TEXT DEFAULT ''",
    "ALTER TABLE journal_entries ADD COLUMN emotions TEXT DEFAULT ''",
    "ALTER TABLE bookings ADD COLUMN psychologist_username TEXT DEFAULT ''",
    "ALTER TABLE patient_profiles ADD COLUMN assigned_psych TEXT DEFAULT ''",
    "ALTER TABLE patient_profiles ADD COLUMN onboarding_step INTEGER DEFAULT 0",
    "ALTER TABLE patient_profiles ADD COLUMN contact_info TEXT DEFAULT ''",
    "ALTER TABLE patient_profiles ADD COLUMN psych_trusted_contact TEXT DEFAULT ''",
    "ALTER TABLE patient_profiles ADD COLUMN encryption_salt TEXT DEFAULT ''",
]


def _run_migrations(db):
    migrations = _MIGRATIONS_PG if BACKEND == "postgres" else _MIGRATIONS_SQLITE
    for sql in migrations:
        try:
            db.execute(sql)
        except Exception:
            pass


def _create_indexes(db):
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_journal_patient ON journal_entries(patient_username)",
        "CREATE INDEX IF NOT EXISTS idx_notes_patient ON clinical_notes(patient_username)",
        "CREATE INDEX IF NOT EXISTS idx_bookings_patient ON bookings(patient_username)",
        "CREATE INDEX IF NOT EXISTS idx_crisis_log_patient ON crisis_log(patient_username)",
        "CREATE INDEX IF NOT EXISTS idx_sensor_session ON ring_sensor_log(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_auth_log_user ON auth_log(username)",
        "CREATE INDEX IF NOT EXISTS idx_auth_log_time ON auth_log(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_activity_actor ON activity_log(actor)",
        "CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_log(timestamp)",
    ]
    for sql in indexes:
        try:
            db.execute(sql)
        except Exception:
            pass


# ── SQLite Backend ────────────────────────────────────────

DB_PATH = os.path.join(DB_DIR, "sentinel.db")


def get_db_path():
    env_path = os.environ.get("SENTINEL_DB_PATH")
    if env_path:
        os.makedirs(os.path.dirname(env_path) or ".", exist_ok=True)
        return env_path
    os.makedirs(DB_DIR, exist_ok=True)
    return DB_PATH


@contextmanager
def _sqlite_connect():
    import sqlite3
    path = get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQLITE)
    wrapper = _CursorWrapper(conn)
    _run_migrations(wrapper)
    _create_indexes(wrapper)
    conn.commit()
    try:
        yield wrapper
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── PostgreSQL Backend ─────────────────────────────────────

_pg_pool = None


def _get_pg_pool():
    global _pg_pool
    if _pg_pool is None:
        from psycopg2.pool import ThreadedConnectionPool
        from psycopg2.extras import RealDictCursor
        _pg_pool = ThreadedConnectionPool(
            minconn=int(os.getenv("SENTINEL_PG_MIN_CONN", "2")),
            maxconn=int(os.getenv("SENTINEL_PG_MAX_CONN", "20")),
            host=os.getenv("SENTINEL_PG_HOST", "localhost"),
            port=int(os.getenv("SENTINEL_PG_PORT", "5432")),
            dbname=os.getenv("SENTINEL_PG_DB", "sentinel"),
            user=os.getenv("SENTINEL_PG_USER", "sentinel"),
            password=os.getenv("SENTINEL_PG_PASSWORD", ""),
            cursor_factory=RealDictCursor,
        )
        conn = _pg_pool.getconn()
        wrapper = _CursorWrapper(conn)
        _ensure_pg_schema(wrapper)
        _pg_pool.putconn(conn)
    return _pg_pool


def _ensure_pg_schema(wrapper):
    for stmt in SCHEMA_PG.split(";"):
        s = stmt.strip()
        if s:
            wrapper.execute(s + ";")
    _run_migrations(wrapper)
    _create_indexes(wrapper)
    wrapper.commit()


@contextmanager
def _pg_connect():
    pool = _get_pg_pool()
    conn = pool.getconn()
    wrapper = _CursorWrapper(conn)
    try:
        yield wrapper
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


# ── Public API ────────────────────────────────────────────

get_db = _pg_connect if BACKEND == "postgres" else _sqlite_connect


def dict_from_row(row):
    if row is None:
        return None
    if BACKEND == "postgres":
        return dict(row) if isinstance(row, dict) else None
    return dict(row)


def list_from_rows(rows):
    return [dict_from_row(r) for r in rows if r]


def init_db():
    pass


def log_auth_event(username: str, event: str, ip_address: str = ""):
    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO auth_log (username, event, ip_address) VALUES (?, ?, ?)",
                (username, event, ip_address)
            )
    except Exception:
        pass


def migrate_from_json():
    from data_manager_ import (
        _safe_read_json, HISTORY_ARCHIVE, CLINICAL_VAULT,
        BOOKINGS_JSON, CRISIS_STATE, CRISIS_LOG, FOLLOWUP_JSON
    )
    with get_db() as db:
        row = db.execute("SELECT COUNT(*) AS cnt FROM journal_entries").fetchone()
        if row and row["cnt"] > 0:
            return

        try:
            archive = _safe_read_json(HISTORY_ARCHIVE, {})
            for patient, entries in archive.items():
                for e in entries:
                    raw = e.get("raw_content", "")
                    enc = encrypt_text(raw)
                    db.execute(
                        "INSERT INTO journal_entries (patient_username, raw_content, summary, hmac, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (patient, enc, e.get("summary", ""), compute_hmac(raw), e.get("timestamp", datetime.now().isoformat()))
                    )
        except Exception:
            pass

        try:
            vault = _safe_read_json(CLINICAL_VAULT, {})
            for psych, notes in vault.items():
                for n in notes:
                    db.execute(
                        "INSERT INTO clinical_notes (psychologist_username, patient_username, raw_notes, ai_synthesis, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (psych, n.get("patient", ""), encrypt_text(n.get("raw_notes", "")), encrypt_text(n.get("ai_synthesis", "")), n.get("timestamp", datetime.now().isoformat()))
                    )
        except Exception:
            pass

        try:
            bookings = _safe_read_json(BOOKINGS_JSON, [])
            for b in bookings:
                db.execute(
                    "INSERT INTO bookings (patient_username, date, time, session_type, members, contact, explanation, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (b.get("patient", ""), b.get("date", ""), b.get("time", ""), b.get("session_type", ""), b.get("members", ""), b.get("contact", ""), b.get("explanation", ""), b.get("status", "Pending"))
                )
        except Exception:
            pass

        try:
            cs = _safe_read_json(CRISIS_STATE, {})
            if cs:
                db.execute(
                    "INSERT INTO crisis_state (active, patient_username, triggered_at, triggered_by, acknowledged, acknowledged_by, acknowledged_at, helpline_escalated, trusted_contact_notified, trustee_acknowledged, trustee_clicked, tc_ack_emailed, helpline_ack_emailed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (1 if cs.get("active") else 0, cs.get("patient", ""), cs.get("triggered_at", ""), cs.get("triggered_by", ""), 1 if cs.get("acknowledged") else 0, cs.get("acknowledged_by", ""), cs.get("acknowledged_at", ""), 1 if cs.get("helpline_escalated") else 0, 1 if cs.get("trusted_contact_notified") else 0, 1 if cs.get("trustee_acknowledged") else 0, 1 if cs.get("trustee_clicked") else 0, 1 if cs.get("tc_ack_emailed") else 0, 1 if cs.get("helpline_ack_emailed") else 0)
                )
        except Exception:
            pass

        try:
            log = _safe_read_json(CRISIS_LOG, [])
            for entry in log:
                db.execute(
                    "INSERT INTO crisis_log (event, patient_username, timestamp, source, details) VALUES (?, ?, ?, ?, ?)",
                    (entry.get("event", ""), entry.get("patient", ""), entry.get("timestamp", datetime.now().isoformat()), entry.get("source", ""), json.dumps(entry.get("details", "")))
                )
        except Exception:
            pass

        try:
            followups = _safe_read_json(FOLLOWUP_JSON, [])
            for t in followups:
                db.execute(
                    "INSERT INTO followups (id, patient_username, psychologist_username, title, description, file_path, status, proof_file, grade, feedback, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (t.get("id", ""), t.get("patient", ""), t.get("psychologist", ""), t.get("title", ""), t.get("description", ""), t.get("file_path", ""), t.get("status", "pending"), t.get("proof_file", ""), t.get("grade", "none"), t.get("feedback", ""), t.get("created_at", datetime.now().isoformat()), t.get("updated_at", datetime.now().isoformat()))
                )
        except Exception:
            pass