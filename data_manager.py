import json
import os
import base64
from datetime import datetime
import uuid

DATA_DIR = "data"
HISTORY_ARCHIVE = os.path.join(DATA_DIR, "history_archive.json")
CLINICAL_VAULT = os.path.join(DATA_DIR, "clinical_vault.json")
BOOKINGS_JSON = os.path.join(DATA_DIR, "bookings.json")
CRISIS_STATE = os.path.join(DATA_DIR, "crisis_state.json")
FOLLOWUP_JSON = os.path.join(DATA_DIR, "followups.json")
KEY_FILE = os.path.join(DATA_DIR, ".encryption_key")


# ── Encryption Layer ─────────────────────────────────────

def _get_key() -> bytes:
    raw = os.getenv("SENTINEL_ENCRYPTION_KEY")
    if raw:
        return raw.encode()
    from cryptography.fernet import Fernet
    return Fernet.generate_key()


def encrypt_text(plain: str) -> str:
    if not plain:
        return plain
    from cryptography.fernet import Fernet
    f = Fernet(_get_key())
    return f.encrypt(plain.encode()).decode()


def decrypt_text(cipher: str) -> str:
    if not cipher:
        return cipher
    from cryptography.fernet import Fernet
    try:
        f = Fernet(_get_key())
        return f.decrypt(cipher.encode()).decode()
    except Exception:
        return cipher


# ── Storage Helpers ──────────────────────────────────────

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _safe_read_json(path, default=None):
    _ensure_dir()
    if default is None:
        default = {} if "vault" in path or "archive" in path else []
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default


def _safe_write_json(path, data):
    _ensure_dir()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


# ── Patient History Archive ──────────────────────────────

def save_journal_entry(patient: str, raw_content: str, summary: str):
    archive = _safe_read_json(HISTORY_ARCHIVE, {})
    if patient not in archive:
        archive[patient] = []
    archive[patient].append({
        "raw_content": encrypt_text(raw_content),
        "summary": summary,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    _safe_write_json(HISTORY_ARCHIVE, archive)


def get_patient_history(patient: str):
    archive = _safe_read_json(HISTORY_ARCHIVE, {})
    entries = archive.get(patient, [])
    for e in entries:
        e["raw_content"] = decrypt_text(e.get("raw_content", ""))
    return entries


def get_all_patient_summaries():
    archive = _safe_read_json(HISTORY_ARCHIVE, {})
    result = {}
    for patient, entries in archive.items():
        result[patient] = [
            {"summary": e["summary"], "timestamp": e["timestamp"]}
            for e in entries
        ]
    return result


# ── Clinical Vault (Psychologist Notes) ──────────────────

def save_clinical_note(psychologist: str, patient: str, raw_notes: str, ai_synthesis: str):
    vault = _safe_read_json(CLINICAL_VAULT, {})
    if psychologist not in vault:
        vault[psychologist] = []
    vault[psychologist].append({
        "patient": patient,
        "raw_notes": encrypt_text(raw_notes),
        "ai_synthesis": ai_synthesis,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    _safe_write_json(CLINICAL_VAULT, vault)


def get_clinical_notes(psychologist: str):
    vault = _safe_read_json(CLINICAL_VAULT, {})
    entries = vault.get(psychologist, [])
    for e in entries:
        e["raw_notes"] = decrypt_text(e.get("raw_notes", ""))
    return entries


# ── Bookings JSON ────────────────────────────────────────

def load_bookings():
    return _safe_read_json(BOOKINGS_JSON, [])


def save_booking(patient: str, date: str, time: str, session_type: str, members: str, contact: str, explanation: str):
    bookings = load_bookings()
    bookings.append({
        "patient": patient,
        "date": date,
        "time": time,
        "session_type": session_type,
        "members": members,
        "contact": contact,
        "explanation": explanation,
        "status": "Pending",
    })
    _safe_write_json(BOOKINGS_JSON, bookings)


def update_booking_status(index: int, new_status: str):
    bookings = load_bookings()
    if 0 <= index < len(bookings):
        bookings[index]["status"] = new_status
        _safe_write_json(BOOKINGS_JSON, bookings)


# ── Crisis State ─────────────────────────────────────────

def get_crisis_state() -> dict:
    return _safe_read_json(CRISIS_STATE, {
        "active": False,
        "patient": "",
        "triggered_at": "",
        "acknowledged": False,
        "acknowledged_by": "",
        "helpline_escalated": False,
        "trusted_contact_notified": False,
        "trustee_clicked": False,
        "trustee_acknowledged": False,
    })


def set_crisis_state(state: dict):
    _safe_write_json(CRISIS_STATE, state)


# ── Follow-ups ──────────────────────────────────────────

def load_followups():
    return _safe_read_json(FOLLOWUP_JSON, [])


def save_followup(patient: str, psychologist: str, title: str, description: str, file_path: str = ""):
    items = load_followups()
    items.append({
        "id": str(uuid.uuid4())[:8],
        "patient": patient,
        "psychologist": psychologist,
        "title": title,
        "description": description,
        "file_path": file_path,
        "status": "pending",
        "proof_file": "",
        "grade": "none",
        "feedback": "",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    })
    _safe_write_json(FOLLOWUP_JSON, items)


def update_followup_status(followup_id: str, new_status: str, proof_file: str = ""):
    items = load_followups()
    for item in items:
        if item["id"] == followup_id:
            item["status"] = new_status
            if proof_file:
                item["proof_file"] = proof_file
            item["updated_at"] = datetime.now().isoformat()
            break
    _safe_write_json(FOLLOWUP_JSON, items)


def update_followup_grade(followup_id: str, grade: str, feedback: str = ""):
    items = load_followups()
    for item in items:
        if item["id"] == followup_id:
            item["grade"] = grade
            if feedback:
                item["feedback"] = feedback
            item["updated_at"] = datetime.now().isoformat()
            break
    _safe_write_json(FOLLOWUP_JSON, items)
