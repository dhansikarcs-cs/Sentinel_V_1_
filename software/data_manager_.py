import json
import os
import uuid
from datetime import datetime
from database import get_db, dict_from_row, list_from_rows, migrate_from_json, encrypt_text, decrypt_text, compute_hmac, verify_hmac

DATA_DIR = "data"
HISTORY_ARCHIVE = os.path.join(DATA_DIR, "history_archive.json")
CLINICAL_VAULT = os.path.join(DATA_DIR, "clinical_vault.json")
BOOKINGS_JSON = os.path.join(DATA_DIR, "bookings.json")
CRISIS_STATE = os.path.join(DATA_DIR, "crisis_state.json")
CRISIS_LOG = os.path.join(DATA_DIR, "crisis_log.json")
FOLLOWUP_JSON = os.path.join(DATA_DIR, "followups.json")


# ── Storage Helpers (kept for migration compat) ──────────

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


_migrated = False


def _ensure_migrated():
    global _migrated
    if not _migrated:
        try:
            migrate_from_json()
        except Exception:
            pass
        _migrated = True


# ── Patient History Archive ──────────────────────────────

def save_journal_entry(username: str, raw_content: str, summary: str):
    _ensure_migrated()
    encrypted = encrypt_text(raw_content)
    hmac_val = compute_hmac(raw_content)
    with get_db() as db:
        db.execute(
            "INSERT INTO journal_entries (patient_username, raw_content, summary, hmac, timestamp) VALUES (?, ?, ?, ?, ?)",
            (username, encrypted, summary, hmac_val, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
    log_activity(username, "journal_entry")


def get_patient_history(username: str):
    _ensure_migrated()
    with get_db() as db:
        rows = db.execute(
            "SELECT raw_content, summary, hmac, timestamp FROM journal_entries WHERE patient_username = ? ORDER BY timestamp ASC",
            (username,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            cipher = d.get("raw_content", "")
            plain = decrypt_text(cipher)
            stored_hmac = d.get("hmac", "")
            if stored_hmac and not verify_hmac(plain, stored_hmac):
                plain = "[TAMPERED]"
            d["raw_content"] = plain
            result.append(d)
        return result


def get_all_patient_summaries():
    _ensure_migrated()
    with get_db() as db:
        rows = db.execute(
            "SELECT patient_username, summary, timestamp FROM journal_entries ORDER BY timestamp ASC"
        ).fetchall()
        result = {}
        for r in rows:
            d = dict(r)
            patient = d["patient_username"]
            if patient not in result:
                result[patient] = []
            result[patient].append({"summary": d["summary"], "timestamp": d["timestamp"]})
        return result


# ── Clinical Vault ───────────────────────────────────────

def save_clinical_note(psychologist: str, patient: str, raw_notes: str, ai_synthesis: str):
    _ensure_migrated()
    with get_db() as db:
        db.execute(
            "INSERT INTO clinical_notes (psychologist_username, patient_username, raw_notes, ai_synthesis, timestamp) VALUES (?, ?, ?, ?, ?)",
            (psychologist, patient, encrypt_text(raw_notes), encrypt_text(ai_synthesis), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
    log_activity(psychologist, "clinical_note", patient)


def get_clinical_notes(psychologist: str):
    _ensure_migrated()
    with get_db() as db:
        rows = db.execute(
            "SELECT patient_username, raw_notes, ai_synthesis, timestamp FROM clinical_notes WHERE psychologist_username = ? ORDER BY timestamp ASC",
            (psychologist,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["patient"] = d.pop("patient_username")
            d["raw_notes"] = decrypt_text(d.get("raw_notes", ""))
            d["ai_synthesis"] = decrypt_text(d.get("ai_synthesis", ""))
            result.append(d)
        return result


# ── Bookings ─────────────────────────────────────────────

def load_bookings():
    _ensure_migrated()
    with get_db() as db:
        rows = db.execute(
            "SELECT id, patient_username, psychologist_username, date, time, session_type, members, contact, explanation, status FROM bookings ORDER BY id ASC"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["patient"] = d.pop("patient_username")
            result.append(d)
        return result


def save_booking(patient: str, date: str, time: str, session_type: str, members: str, contact: str, explanation: str, status: str = "Pending", psychologist_username: str = ""):
    _ensure_migrated()
    with get_db() as db:
        db.execute(
            "INSERT INTO bookings (patient_username, psychologist_username, date, time, session_type, members, contact, explanation, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (patient, psychologist_username, date, time, session_type, members, contact, explanation, status)
        )
    log_activity(psychologist_username or patient, "booking_created", patient, f"{date} {time} ({status})")


def update_booking_status_by_id(booking_id: int, new_status: str):
    _ensure_migrated()
    with get_db() as db:
        row = db.execute("SELECT patient_username, psychologist_username FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        db.execute("UPDATE bookings SET status = ? WHERE id = ?", (new_status, booking_id))
    if row:
        d = dict(row)
        patient = d["patient_username"]
        psych = d["psychologist_username"] or ""
        log_activity(psych or patient, "booking_status", patient, f"{new_status}")


def load_bookings_for_patient(patient: str):
    _ensure_migrated()
    with get_db() as db:
        rows = db.execute(
            "SELECT id, patient_username, psychologist_username, date, time, session_type, members, contact, explanation, status FROM bookings WHERE patient_username = ? ORDER BY id ASC",
            (patient,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["patient"] = d.pop("patient_username")
            result.append(d)
        return result


def update_booking_status(index: int, new_status: str):
    _ensure_migrated()
    with get_db() as db:
        row = db.execute("SELECT id FROM bookings ORDER BY id ASC LIMIT 1 OFFSET ?", (index,)).fetchone()
        if row:
            db.execute("UPDATE bookings SET status = ? WHERE id = ?", (new_status, row["id"]))


# ── Psych Availability ──────────────────────────────────

def save_psych_availability(psychologist_username: str, date_str: str, start_time: str = "09:00", end_time: str = "17:00"):
    _ensure_migrated()
    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM psych_availability WHERE psychologist_username = ? AND date = ?",
            (psychologist_username, date_str)
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE psych_availability SET start_time = ?, end_time = ? WHERE id = ?",
                (start_time, end_time, existing["id"])
            )
        else:
            db.execute(
                "INSERT INTO psych_availability (psychologist_username, date, start_time, end_time) VALUES (?, ?, ?, ?)",
                (psychologist_username, date_str, start_time, end_time)
            )


def delete_psych_availability(psychologist_username: str, date_str: str):
    _ensure_migrated()
    with get_db() as db:
        db.execute(
            "DELETE FROM psych_availability WHERE psychologist_username = ? AND date = ?",
            (psychologist_username, date_str)
        )


def load_psych_availability(psychologist_username: str):
    _ensure_migrated()
    with get_db() as db:
        rows = db.execute(
            "SELECT date, start_time, end_time FROM psych_availability WHERE psychologist_username = ? ORDER BY date ASC",
            (psychologist_username,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_available_psychologists(clinic_code: str):
    """For a given clinic code, find psychologists who have marked any availability."""
    _ensure_migrated()
    with get_db() as db:
        rows = db.execute(
            "SELECT DISTINCT p.username, p.name FROM patient_profiles p "
            "INNER JOIN psych_availability a ON p.username = a.psychologist_username "
            "WHERE p.role = 'psychologist' AND p.clinic_code = ? "
            "ORDER BY p.name",
            (clinic_code,)
        ).fetchall()
        return [{"username": r["username"], "name": r["name"]} for r in rows]


# ── Crisis Log ───────────────────────────────────────────

def load_crisis_log():
    _ensure_migrated()
    with get_db() as db:
        rows = db.execute(
            "SELECT event, patient_username, timestamp, source, details FROM crisis_log ORDER BY id ASC"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["patient"] = d.pop("patient_username", "")
            try:
                d["details"] = json.loads(d.get("details", "{}"))
            except Exception:
                pass
            result.append(d)
        return result


def append_crisis_log(entry: dict):
    _ensure_migrated()
    with get_db() as db:
        db.execute(
            "INSERT INTO crisis_log (event, patient_username, timestamp, source, details) VALUES (?, ?, ?, ?, ?)",
            (entry.get("event", ""), entry.get("patient", ""), entry.get("timestamp", datetime.now().isoformat()), entry.get("source", ""), json.dumps(entry.get("details", "")))
        )


# ── Crisis State ─────────────────────────────────────────

def get_crisis_state() -> dict:
    _ensure_migrated()
    with get_db() as db:
        row = db.execute("SELECT * FROM crisis_state ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            return {
                "active": False, "patient": "", "triggered_at": "", "triggered_by": "",
                "acknowledged": False, "acknowledged_by": "", "acknowledged_at": "",
                "helpline_escalated": False, "trusted_contact_notified": False,
                "trustee_acknowledged": False, "trustee_clicked": False,
                "tc_ack_emailed": False, "helpline_ack_emailed": False,
            }
        d = dict(row)
        d["active"] = bool(d["active"])
        d["acknowledged"] = bool(d["acknowledged"])
        d["helpline_escalated"] = bool(d["helpline_escalated"])
        d["trusted_contact_notified"] = bool(d["trusted_contact_notified"])
        d["trustee_acknowledged"] = bool(d["trustee_acknowledged"])
        d["trustee_clicked"] = bool(d["trustee_clicked"])
        d["tc_ack_emailed"] = bool(d["tc_ack_emailed"])
        d["helpline_ack_emailed"] = bool(d["helpline_ack_emailed"])
        d["patient"] = d.pop("patient_username", "")
        return d


def set_crisis_state(state: dict):
    _ensure_migrated()
    with get_db() as db:
        row = db.execute("SELECT id FROM crisis_state ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            db.execute(
                "UPDATE crisis_state SET active=?, patient_username=?, triggered_at=?, triggered_by=?, acknowledged=?, acknowledged_by=?, acknowledged_at=?, helpline_escalated=?, trusted_contact_notified=?, trustee_acknowledged=?, trustee_clicked=?, tc_ack_emailed=?, helpline_ack_emailed=? WHERE id=?",
                (1 if state.get("active") else 0, state.get("patient", ""), state.get("triggered_at", ""), state.get("triggered_by", ""), 1 if state.get("acknowledged") else 0, state.get("acknowledged_by", ""), state.get("acknowledged_at", ""), 1 if state.get("helpline_escalated") else 0, 1 if state.get("trusted_contact_notified") else 0, 1 if state.get("trustee_acknowledged") else 0, 1 if state.get("trustee_clicked") else 0, 1 if state.get("tc_ack_emailed") else 0, 1 if state.get("helpline_ack_emailed") else 0, row["id"])
            )
        else:
            db.execute(
                "INSERT INTO crisis_state (active, patient_username, triggered_at, triggered_by, acknowledged, acknowledged_by, acknowledged_at, helpline_escalated, trusted_contact_notified, trustee_acknowledged, trustee_clicked, tc_ack_emailed, helpline_ack_emailed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (1 if state.get("active") else 0, state.get("patient", ""), state.get("triggered_at", ""), state.get("triggered_by", ""), 1 if state.get("acknowledged") else 0, state.get("acknowledged_by", ""), state.get("acknowledged_at", ""), 1 if state.get("helpline_escalated") else 0, 1 if state.get("trusted_contact_notified") else 0, 1 if state.get("trustee_acknowledged") else 0, 1 if state.get("trustee_clicked") else 0, 1 if state.get("tc_ack_emailed") else 0, 1 if state.get("helpline_ack_emailed") else 0)
            )


# ── Follow-ups ──────────────────────────────────────────

def load_followups():
    _ensure_migrated()
    with get_db() as db:
        rows = db.execute("SELECT * FROM followups ORDER BY created_at ASC").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["patient"] = d.pop("patient_username")
            d["psychologist"] = d.pop("psychologist_username")
            result.append(d)
        return result


def save_followup(patient: str, psychologist: str, title: str, description: str, file_path: str = ""):
    _ensure_migrated()
    fid = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    with get_db() as db:
        db.execute(
            "INSERT INTO followups (id, patient_username, psychologist_username, title, description, file_path, status, proof_file, grade, feedback, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', '', 'none', '', ?, ?)",
            (fid, patient, psychologist, title, description, file_path, now, now)
        )
    log_activity(psychologist, "followup_created", patient, title)


def update_followup_status(followup_id: str, new_status: str, proof_file: str = ""):
    _ensure_migrated()
    now = datetime.now().isoformat()
    with get_db() as db:
        if proof_file:
            db.execute("UPDATE followups SET status=?, proof_file=?, updated_at=? WHERE id=?", (new_status, proof_file, now, followup_id))
        else:
            db.execute("UPDATE followups SET status=?, updated_at=? WHERE id=?", (new_status, now, followup_id))


def update_followup_grade(followup_id: str, grade: str, feedback: str = ""):
    _ensure_migrated()
    now = datetime.now().isoformat()
    with get_db() as db:
        if feedback:
            db.execute("UPDATE followups SET grade=?, feedback=?, updated_at=? WHERE id=?", (grade, feedback, now, followup_id))
        else:
            db.execute("UPDATE followups SET grade=?, updated_at=? WHERE id=?", (grade, now, followup_id))


# ── Activity Log ──────────────────────────────────────────

def log_activity(actor: str, action: str, target: str = "", detail: str = ""):
    _ensure_migrated()
    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO activity_log (actor, action, target, detail, timestamp) VALUES (?, ?, ?, ?, ?)",
                (actor, action, target, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
    except Exception:
        pass


def get_activity_feed(actor: str = "", limit: int = 50):
    _ensure_migrated()
    with get_db() as db:
        if actor:
            rows = db.execute(
                "SELECT actor, action, target, detail, timestamp FROM activity_log WHERE actor = ? ORDER BY timestamp DESC LIMIT ?",
                (actor, limit)
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT actor, action, target, detail, timestamp FROM activity_log ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]