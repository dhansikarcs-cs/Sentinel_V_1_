import hashlib
import os
import string
import random as _random
from datetime import datetime, timedelta
from database import get_db, log_auth_event

SALT = os.getenv("SENTINEL_PASSWORD_SALT", "sentinel-fixed-salt").encode()

AUTH_ATTEMPT_LIMIT = 5
AUTH_LOCKOUT_MINUTES = 15


def _hash_password(password: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), SALT, 100000).hex()


def _is_locked(username: str) -> bool:
    with get_db() as db:
        row = db.execute(
            "SELECT locked_until FROM patient_profiles WHERE username = ?", (username,)
        ).fetchone()
        if row and row["locked_until"]:
            try:
                lock_time = datetime.fromisoformat(row["locked_until"])
                if datetime.now() < lock_time:
                    return True
            except (ValueError, TypeError):
                pass
    return False


def _check_rate_limit(username: str) -> bool:
    with get_db() as db:
        cutoff = (datetime.now() - timedelta(minutes=AUTH_LOCKOUT_MINUTES)).isoformat()
        recent = db.execute(
            "SELECT COUNT(*) AS cnt FROM auth_log WHERE username = ? AND event = 'failed_login' AND timestamp > ?",
            (username, cutoff)
        ).fetchone()["cnt"]
        return recent < AUTH_ATTEMPT_LIMIT


def _reset_failures(username: str):
    with get_db() as db:
        db.execute("UPDATE patient_profiles SET failed_attempts = 0, locked_until = '' WHERE username = ?", (username,))


def _record_failure(username: str):
    with get_db() as db:
        row = db.execute("SELECT failed_attempts FROM patient_profiles WHERE username = ?", (username,)).fetchone()
        attempts = (row["failed_attempts"] if row else 0) + 1
        lock_until = ""
        if attempts >= AUTH_ATTEMPT_LIMIT:
            lock_until = (datetime.now() + timedelta(minutes=AUTH_LOCKOUT_MINUTES)).isoformat()
        db.execute(
            "UPDATE patient_profiles SET failed_attempts = ?, locked_until = ? WHERE username = ?",
            (attempts, lock_until, username)
        )


def _gen_code(length=8):
    chars = string.ascii_uppercase + string.digits
    return ''.join(_random.choices(chars, k=length))


CLINIC_NAMES = ["CLINIC_ALPHA", "CLINIC_BETA", "CLINIC_GAMMA", "CLINIC_DELTA", "CLINIC_EPSILON"]


def _seed_clinic_codes():
    with get_db() as db:
        existing = db.execute("SELECT COUNT(*) AS cnt FROM clinic_codes").fetchone()["cnt"]
        if existing > 0:
            return
        for c in CLINIC_NAMES:
            db.execute("INSERT INTO clinic_codes (code) VALUES (?)", (c,))
        print(f"[sentinel] Clinic codes: {', '.join(CLINIC_NAMES)}", flush=True)


PROFESSION_NAMES = ["PROF_PSYCH_001", "PROF_PSYCH_002", "PROF_PSYCH_003", "PROF_PSYCH_004", "PROF_PSYCH_005", "PROF_COUNSELOR_001", "PROF_THERAPIST_001"]


def _seed_profession_codes():
    with get_db() as db:
        existing = db.execute("SELECT COUNT(*) AS cnt FROM profession_codes").fetchone()["cnt"]
        if existing > 0:
            return
        for c in PROFESSION_NAMES:
            db.execute("INSERT INTO profession_codes (code) VALUES (?)", (c,))
        print(f"[sentinel] Profession codes: {', '.join(PROFESSION_NAMES)}", flush=True)


TEST_FIRST_NAMES = [
    "Emma","Liam","Olivia","Noah","Ava","Ethan","Sophia","Mason","Isabella","Logan",
    "Mia","Lucas","Charlotte","James","Amelia","Benjamin","Harper","Elijah","Evelyn","Alexander",
]
TEST_LAST_NAMES = [
    "Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
    "Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin",
]
OCCUPATIONS = [
    "Engineer","Teacher","Designer","Doctor","Student","Writer","Artist","Nurse",
    "Manager","Analyst","Developer","Researcher","Consultant","Chef","Pilot",
]


def _seed_test_accounts():
    with get_db() as db:
        existing = db.execute("SELECT COUNT(*) AS cnt FROM patient_profiles").fetchone()["cnt"]
        if existing > 0:
            return
        _seed_clinic_codes()
        _seed_profession_codes()
        clinic_rows = db.execute("SELECT code FROM clinic_codes ORDER BY code").fetchall()
        clinic_codes = [r["code"] for r in clinic_rows]
        ps = _random.Random(42)
        count = 0
        clinic_patient_map = {
            "CLINIC_ALPHA": {
                "psychs": ["test_psych_1", "test_psych_2", "test_psych_3", "test_psych_4", "test_psych_5"],
                "patients": list(range(1, 21)),
            },
        }
        psych_prof_codes = ["PROF_PSYCH_001", "PROF_PSYCH_002", "PROF_PSYCH_003", "PROF_PSYCH_004", "PROF_PSYCH_005"]
        for cc, mapping in clinic_patient_map.items():
            psych_usernames = list(mapping["psychs"])
            for idx, pnum in enumerate(mapping["patients"]):
                uname = f"test_patient_{pnum}"
                pw = "test123"
                fname = ps.choice(TEST_FIRST_NAMES)
                lname = ps.choice(TEST_LAST_NAMES)
                name = f"{fname} {lname}"
                age = ps.randint(18, 65)
                occ = ps.choice(OCCUPATIONS)
                h = _hash_password(pw)
                assigned = psych_usernames[idx % len(psych_usernames)]
                db.execute(
                    "INSERT INTO patient_profiles (username, password_hash, name, role, age, occupation, clinic_code, assigned_psych) VALUES (?, ?, ?, 'patient', ?, ?, ?, ?)",
                    (uname, h, name, age, occ, cc, assigned)
                )
                count += 1
            for psych_idx, psych_uname in enumerate(mapping["psychs"]):
                pw = "doc123"
                fname = ps.choice(TEST_FIRST_NAMES)
                lname = ps.choice(TEST_LAST_NAMES)
                name = f"Dr. {fname} {lname}"
                age = ps.randint(30, 60)
                occ = "Psychologist"
                h = _hash_password(pw)
                db.execute(
                    "INSERT INTO patient_profiles (username, password_hash, name, role, age, occupation, clinic_code) VALUES (?, ?, ?, 'psychologist', ?, ?, ?)",
                    (psych_uname, h, name, age, occ, cc)
                )
                if psych_idx < len(psych_prof_codes):
                    db.execute("UPDATE profession_codes SET used = 1 WHERE code = ?", (psych_prof_codes[psych_idx],))
                count += 1
        for i in range(5):
            uname = f"test_extra_{i+1}"
            pw = "extra123"
            fname = ps.choice(TEST_FIRST_NAMES)
            lname = ps.choice(TEST_LAST_NAMES)
            name = f"{fname} {lname}"
            age = ps.randint(18, 70)
            occ = ps.choice(OCCUPATIONS)
            role = ps.choice(["patient", "psychologist"])
            cc = clinic_codes[i % len(clinic_codes)]
            h = _hash_password(pw)
            db.execute(
                "INSERT INTO patient_profiles (username, password_hash, name, role, age, occupation, clinic_code) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (uname, h, name, role, age, occ, cc)
            )
            count += 1
        print(f"[sentinel] Seeded {count} test accounts (20 patients + 5 psychologists + 5 extra)", flush=True)
        for cc, mapping in clinic_patient_map.items():
            psych_names = []
            for psych_uname in mapping["psychs"]:
                row = db.execute("SELECT name FROM patient_profiles WHERE username = ?", (psych_uname,)).fetchone()
                if row:
                    psych_names.append(row["name"])
            pnames = []
            for pnum in mapping["patients"]:
                row = db.execute("SELECT name FROM patient_profiles WHERE username = ?", (f"test_patient_{pnum}",)).fetchone()
                if row:
                    pnames.append(row["name"])
            print(f"  {cc}: {', '.join(psych_names)} - {', '.join(pnames)}", flush=True)
            for psych_uname in mapping["psychs"]:
                row = db.execute("SELECT name FROM patient_profiles WHERE username = ?", (psych_uname,)).fetchone()
                if row:
                    print(f"    {psych_uname} -> {row['name']}", flush=True)


def validate_clinic_code(code: str) -> bool:
    with get_db() as db:
        row = db.execute("SELECT 1 FROM clinic_codes WHERE code = ?", (code,)).fetchone()
        return bool(row)


def validate_profession_code(code: str) -> bool:
    with get_db() as db:
        row = db.execute("SELECT used FROM profession_codes WHERE code = ?", (code,)).fetchone()
        return bool(row and row["used"] == 0)


def register_user(username, password, name, age, occupation, role, clinic_code, profession_code=None, assigned_psych=""):
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if not validate_clinic_code(clinic_code):
        return False, "Invalid clinic code."
    if role == "psychologist":
        if not profession_code or not validate_profession_code(profession_code):
            return False, "Invalid or already used profession code."
    elif role == "patient" and not assigned_psych:
        return False, "Please select a psychologist."
    with get_db() as db:
        existing = db.execute("SELECT username FROM patient_profiles WHERE username = ?", (username,)).fetchone()
        if existing:
            return False, "Username already taken."
        h = _hash_password(password)
        if role == "patient":
            db.execute(
                "INSERT INTO patient_profiles (username, password_hash, name, role, age, occupation, clinic_code, assigned_psych) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (username, h, name, role, age, occupation, clinic_code, assigned_psych)
            )
        else:
            db.execute(
                "INSERT INTO patient_profiles (username, password_hash, name, role, age, occupation, clinic_code) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (username, h, name, role, age, occupation, clinic_code)
            )
        if role == "psychologist" and profession_code:
            db.execute("UPDATE profession_codes SET used = 1 WHERE code = ?", (profession_code,))
    return True, "Registration successful! You can now sign in."


def _load_profiles():
    _seed_test_accounts()


def authenticate(username: str, password: str, ip_address: str = ""):
    if _is_locked(username):
        log_auth_event(username, "locked_attempt", ip_address)
        return None
    if not _check_rate_limit(username):
        log_auth_event(username, "rate_limited", ip_address)
        return None
    h = _hash_password(password)
    with get_db() as db:
        row = db.execute(
            "SELECT role FROM patient_profiles WHERE username = ? AND password_hash = ?",
            (username, h)
        ).fetchone()
        if row:
            _reset_failures(username)
            role = row["role"]
            log_auth_event(username, "successful_login", ip_address)
            return "Patient" if role == "patient" else "Psychologist"
    _record_failure(username)
    log_auth_event(username, "failed_login", ip_address)
    return None


def change_password(username: str, old_password: str, new_password: str) -> bool:
    if not authenticate(username, old_password):
        return False
    new_h = _hash_password(new_password)
    with get_db() as db:
        db.execute("UPDATE patient_profiles SET password_hash = ? WHERE username = ?", (new_h, username))
    return True


def get_patient_name(username: str) -> str:
    with get_db() as db:
        row = db.execute("SELECT name FROM patient_profiles WHERE username = ?", (username,)).fetchone()
        return row["name"] if row else username


def get_psychologist_name(username: str) -> str:
    with get_db() as db:
        row = db.execute("SELECT name FROM patient_profiles WHERE username = ? AND role = 'psychologist'", (username,)).fetchone()
        return row["name"] if row else username


def get_trusted_contact(patient_username: str) -> str:
    with get_db() as db:
        row = db.execute("SELECT trusted_contact FROM patient_profiles WHERE username = ? AND role = 'patient'", (patient_username,)).fetchone()
        return row["trusted_contact"] if row else ""


def set_trusted_contact(username: str, contact: str):
    with get_db() as db:
        db.execute("UPDATE patient_profiles SET trusted_contact = ? WHERE username = ? AND role = 'patient'", (contact, username))


def get_any_trusted_contact(username: str) -> str:
    with get_db() as db:
        row = db.execute("SELECT trusted_contact FROM patient_profiles WHERE username = ?", (username,)).fetchone()
        return row["trusted_contact"] if row else ""


def set_any_trusted_contact(username: str, contact: str):
    with get_db() as db:
        db.execute("UPDATE patient_profiles SET trusted_contact = ? WHERE username = ?", (contact, username))


def get_all_patients():
    with get_db() as db:
        rows = db.execute("SELECT username FROM patient_profiles WHERE role = 'patient'").fetchall()
        return [r["username"] for r in rows]


def get_assigned_patients(psych_username: str):
    with get_db() as db:
        rows = db.execute("SELECT username FROM patient_profiles WHERE role = 'patient' AND assigned_psych = ?", (psych_username,)).fetchall()
        return [r["username"] for r in rows]


def get_patient_clinic(username: str) -> str:
    with get_db() as db:
        row = db.execute("SELECT clinic_code FROM patient_profiles WHERE username = ?", (username,)).fetchone()
        return row["clinic_code"] if row else ""


def get_clinic_psychologists(clinic_code: str):
    with get_db() as db:
        rows = db.execute("SELECT username, name FROM patient_profiles WHERE role = 'psychologist' AND clinic_code = ?", (clinic_code,)).fetchall()
        return [{"username": r["username"], "name": r["name"]} for r in rows]


def get_all_psychologists():
    with get_db() as db:
        rows = db.execute("SELECT username, name, clinic_code FROM patient_profiles WHERE role = 'psychologist'").fetchall()
        return [{"username": r["username"], "name": r["name"], "clinic_code": r["clinic_code"] if r["clinic_code"] else ""} for r in rows]


def get_clinic_psychs_for_registration(clinic_code: str):
    with get_db() as db:
        rows = db.execute("SELECT username, name FROM patient_profiles WHERE role = 'psychologist' AND clinic_code = ?", (clinic_code,)).fetchall()
        return [{"username": r["username"], "name": r["name"]} for r in rows]


def get_assigned_psych(username: str) -> str:
    with get_db() as db:
        row = db.execute("SELECT assigned_psych FROM patient_profiles WHERE username = ? AND role = 'patient'", (username,)).fetchone()
        return row["assigned_psych"] if row else ""


def get_onboarding_step(username: str) -> int:
    with get_db() as db:
        row = db.execute("SELECT onboarding_step FROM patient_profiles WHERE username = ?", (username,)).fetchone()
        return row["onboarding_step"] if row else 0


def set_onboarding_step(username: str, step: int):
    with get_db() as db:
        db.execute("UPDATE patient_profiles SET onboarding_step = ? WHERE username = ?", (step, username))


def get_contact_info(username: str) -> str:
    with get_db() as db:
        row = db.execute("SELECT contact_info FROM patient_profiles WHERE username = ?", (username,)).fetchone()
        return row["contact_info"] if row else ""


def set_contact_info(username: str, contact: str):
    with get_db() as db:
        db.execute("UPDATE patient_profiles SET contact_info = ? WHERE username = ?", (contact, username))


def get_psych_trusted_contact(username: str) -> str:
    with get_db() as db:
        row = db.execute("SELECT psych_trusted_contact FROM patient_profiles WHERE username = ?", (username,)).fetchone()
        return row["psych_trusted_contact"] if row else ""


def set_psych_trusted_contact(username: str, contact: str):
    with get_db() as db:
        db.execute("UPDATE patient_profiles SET psych_trusted_contact = ? WHERE username = ?", (contact, username))


_load_profiles()