# Sentinel — Per-File Code Explanation

Every function, every block, every key line explained.

> **Note:** This codebook documents the original Streamlit prototype (`database.py`, `ai_kernel_.py`, `patient_journal_.py`, ...), which was superseded by the FastAPI + React architecture and archived under `archive/`. For the current stack, see `README.md` (structure), `docs/TECHNICAL_DESIGN.md`, and `docs/ENGINEERING_DECISIONS.md`. The ring SDK (current `app/services/ring/`) is documented in `docs/ROADMAP_HARDWARE.md` and `docs/TECHNICAL_DESIGN.md` §13.

---

## `database.py` — Database Schema & Connection (200 lines)

### Imports & Constants (1-15)

```python
import sqlite3, os, atexit
from datetime import datetime
```

Two schema dictionaries define the same tables for SQLite and PostgreSQL:
```python
SCHEMA_SQLITE = {
    "patient_profiles": """
        CREATE TABLE IF NOT EXISTS patient_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            role TEXT NOT NULL DEFAULT 'patient',
            age INTEGER,
            occupation TEXT,
            clinic_code TEXT,
            ...
        )
    """,
    "mood_log": """
        CREATE TABLE IF NOT EXISTS mood_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_username TEXT NOT NULL,
            date TEXT NOT NULL,
            emoji TEXT NOT NULL,
            label TEXT NOT NULL,
            timestamp TEXT DEFAULT (datetime('now')),
            UNIQUE(patient_username, date)
        )
    """,
    # ... 15 tables total
}
```

15 tables: `patient_profiles`, `clinic_codes`, `profession_codes`, `journal_entries`,
`clinical_notes`, `bookings`, `psych_availability`, `crisis_state`, `crisis_log`,
`followups`, `ring_sessions`, `ring_sensor_log`, `auth_log`, `activity_log`, `mood_log`.

### `get_db()` — Connection context manager (28-55)

```python
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)  # or psycopg2 for PostgreSQL
    conn.row_factory = sqlite3.Row   # Access columns by name: row["username"]
    try:
        yield conn                   # Provide connection to caller
        conn.commit()                # Auto-commit on success
    except Exception:
        conn.rollback()              # Rollback on error
        raise
    finally:
        conn.close()                 # Always close
```

### `init_db()` — Schema creation (58-80)

```python
def init_db():
    with get_db() as db:
        for name, ddl in SCHEMA_SQLITE.items():
            db.execute(ddl)           # CREATE TABLE IF NOT EXISTS for each table
        _seed_clinic_codes(db)        # Insert clinic codes if empty
        _seed_profession_codes(db)    # Insert profession codes if empty
```

---

## `patient_profiles_.py` — Auth & User Management (370 lines)

### `_hash_password(password)` — PBKDF2 hashing (8-18)

```python
def _hash_password(password: str) -> str:
    salt = os.getenv("SENTINEL_PASSWORD_SALT", "sentinel_default_salt")
    key = hashlib.pbkdf2_hmac(
        "sha256",                         # Hash algorithm
        password.encode("utf-8"),         # Raw password bytes
        salt.encode("utf-8"),             # Salt bytes
        100000,                           # 100k iterations (slow, resists brute force)
        dklen=32                          # 32-byte output
    )
    return base64.b64encode(key).decode()  # Store as base64 string in DB
```

### `authenticate(username, password)` — Login (44-55)

```python
def authenticate(username: str, password: str):
    with get_db() as db:
        row = db.execute(
            "SELECT password_hash, role FROM patient_profiles WHERE username = ?",
            (username,)
        ).fetchone()
        if row and row["password_hash"] == _hash_password(password):
            return row["role"]             # "patient" or "psychologist"
    return None                            # Wrong user or password
```

### `_seed_test_accounts()` — Test data (115-195)

Seeds 20 patients + 5 psychologists + 5 extras under `CLINIC_ALPHA`.
Each patient gets a rotating assigned psychologist from the 5 test psychs:

```python
clinic_patient_map = {
    "CLINIC_ALPHA": {
        "psychs": ["test_psych_1", ..., "test_psych_5"],
        "patients": list(range(1, 21)),    # test_patient_1 through test_patient_20
    },
}
for idx, pnum in enumerate(mapping["patients"]):
    assigned = psych_usernames[idx % len(psych_usernames)]  # Round-robin assignment
    # ...
    db.execute(
        "INSERT INTO patient_profiles (...) VALUES (...) WITH assigned_psych",
        (uname, h, name, age, occ, cc, assigned)
    )
```

### `register_user(username, password, ...)` — Registration (200-230)

```python
def register_user(username, password, name, age, occupation, role, clinic_code, profession_code=None, assigned_psych=""):
    if len(username) < 3: return False, "Username must be at least 3 characters."
    if len(password) < 6: return False, "Password must be at least 6 characters."
    if not validate_clinic_code(clinic_code): return False, "Invalid clinic code."
    if role == "psychologist" and not validate_profession_code(profession_code):
        return False, "Invalid profession code."
    if role == "patient" and not assigned_psych:
        return False, "Please select a psychologist."
    # Insert into DB with PBKDF2 hash
    db.execute("INSERT INTO patient_profiles (...) VALUES (...)", (...))
```

### New functions added (v3):

```python
def get_assigned_patients(psych_username: str) -> list:
    # Returns list of patient usernames assigned to this psychologist
    rows = db.execute("SELECT username FROM patient_profiles WHERE role='patient' AND assigned_psych=?", (psych_username,))
    return [r["username"] for r in rows]

def get_clinic_psychs_for_registration(clinic_code: str) -> list:
    # Returns psychs in a clinic for the patient registration dropdown
    rows = db.execute("SELECT username, name FROM patient_profiles WHERE role='psychologist' AND clinic_code=?", (clinic_code,))
    return [{"username": r["username"], "name": r["name"]} for r in rows]

def get_assigned_psych(username: str) -> str:
    # Returns which psych this patient is assigned to
    row = db.execute("SELECT assigned_psych FROM patient_profiles WHERE username=? AND role='patient'")
    return row["assigned_psych"] if row else ""

def validate_clinic_code(code: str) -> bool:
    # Now: codes are reusable — just checks existence
    row = db.execute("SELECT 1 FROM clinic_codes WHERE code=?", (code,))
    return bool(row)
```

---

## `data_manager_.py` — Database Operations (280 lines)

**Before (v2):** JSON file storage with `_safe_read_json` / `_safe_write_json`.
**Now (v3):** All operations use `database.get_db()` for SQL queries.

### `save_journal_entry(patient, raw_content, summary)` — Save journal (10-25)

```python
def save_journal_entry(patient: str, raw_content: str, summary: str):
    with get_db() as db:
        encrypted = encrypt_text(raw_content)      # Fernet encryption
        db.execute(
            "INSERT INTO journal_entries (patient_username, raw_content, summary, timestamp) VALUES (?, ?, ?, ?)",
            (patient, encrypted, summary, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
```

### `get_patient_history(patient)` — Load patient journals (30-45)

```python
def get_patient_history(patient: str):
    with get_db() as db:
        rows = db.execute(
            "SELECT raw_content, summary, timestamp FROM journal_entries WHERE patient_username=? ORDER BY timestamp DESC",
            (patient,)
        ).fetchall()
        entries = [dict(r) for r in rows]
        for e in entries:
            e["raw_content"] = decrypt_text(e.get("raw_content", ""))  # Decrypt on read
        return entries
```

### `save_mood(username, emoji, label)` — Daily mood upsert (50-65)

```python
def save_mood(username: str, emoji: str, label: str):
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as db:
        db.execute(
            "INSERT INTO mood_log (patient_username, date, emoji, label) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(patient_username, date) DO UPDATE SET emoji=excluded.emoji, label=excluded.label, timestamp=datetime('now')",
            (username, today, emoji, label)
        )
```

`ON CONFLICT ... DO UPDATE` is SQLite-specific UPSERT — if the patient already has a mood for today, it overwrites instead of inserting a duplicate.

### `get_today_mood(username)` — Get today's mood (70-80)

```python
def get_today_mood(username: str):
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as db:
        row = db.execute(
            "SELECT emoji, label FROM mood_log WHERE patient_username=? AND date=?",
            (username, today)
        ).fetchone()
        return dict(row) if row else None
```

Returns `None` if no mood logged today. The caller checks `is not None` to determine lock state.

---

## `ai_kernel_.py` — AI Engine (250 lines)

### Model & Timeout Changes (v2→v3)

```python
OLLAMA_MODEL = "sentinel"          # Was "mistral". Now a custom 7.2B therapy-tuned model
```

Timeouts increased from 3s to 30s:
```python
client = Groq(api_key=key, timeout=30, max_retries=0)  # Was timeout=3
```

### `_get_emotion_labels(text)` — Emotion classifier integration (55-65)

```python
def _get_emotion_labels(text: str) -> str:
    try:
        from emotion_classifier import classify_text as _ct
        return _ct(text)             # Returns comma-separated GoEmotions labels
    except Exception:
        return ""
```

### `summarize_journal(raw_text, mode)` — Two-mode summarization (70-130)

**New `mode` parameter:** `"patient"` for warm reflection, `"clinical"` for OAP clinical notes.

```python
if mode == "clinical":
    prompt = (
        "You are Sentinel, a clinical documentation AI. Read this journal entry "
        "and write a brief clinical summary (2-4 sentences)."
        f"{emotion_hint}"                              # Emotion labels from classifier
        " Use clinical tone, third person, past tense. Do not quote verbatim."
        f"\n\nJournal Entry:\n{raw_text}"
        f"\n\nClinical Summary:"
    )
else:
    prompt = (
        "You are Sentinel, an emotionally intelligent assistant. Read this journal entry "
        "and write a brief, warm reflection (2-4 sentences)."
        f"{emotion_hint}"
        " Acknowledge and validate their feelings. No advice whatsoever — "
        "no suggestions, no 'try this', no 'consider that', no 'remember to', "
        "no coping techniques, no deep breaths. Zero prescription. Just sit with them."
        f"\n\nJournal Entry:\n{raw_text}"
        f"\n\nReflection:"
    )
```

The patient mode has a strict "no advice" constraint — the AI is told to validate feelings without providing any suggestions or coping strategies.

### `_is_raw_echo(output, original)` — Echo detection (140-155)

```python
def _is_raw_echo(output: str, original: str) -> bool:
    cleaned = output.strip().lower()
    orig_clean = original.strip().lower()
    if cleaned == orig_clean:          # Exact match
        return True
    if cleaned in orig_clean:          # Output is substring of original
        return True
    if orig_clean in cleaned:          # Original is substring of output
        return True
    # Word overlap > 85% → echo
    out_words = set(re.findall(r'\w+', cleaned))
    orig_words = set(re.findall(r'\w+', orig_clean))
    overlap = len(out_words & orig_words) / len(orig_words)
    return overlap > 0.85
```

Prevents the AI from simply echoing the user's journal text back as a "summary".

### `_fallback_summary(text, emotions, mode)` — Rule fallback (200-230)

Updated to use the mode parameter and emotion hints:

```python
if mode == "clinical":
    return f"**Observations**: {emotions}...\n**Assessment**: ...\n**Plan**: ..."
if emotions:
    return f"Emotions detected: {emotions}. Brief entry noted."
return "Brief entry noted. Monitor mood trends."
```

---

## `patient_journal_.py` — Journal & Mood Module (160 lines)

### `MOODS` — Emoji options (18-25)

```python
MOODS = [
    ("\U0001f622", "Sad"),     # 😢
    ("\U0001f641", "Down"),    # 🙁
    ("\U0001f610", "Okay"),    # 😐
    ("\U0001f642", "Good"),    # 🙂
    ("\U0001f601", "Great"),   # 😁
]
```

### `render_patient_journal(username)` — Main render function (27-148)

**Mood lock flow (37-68):**

```python
today_mood = safe(get_today_mood, None, username)
mood_locked = today_mood is not None

if mood_locked:
    # "locked for today" label
    st.markdown("... locked for today ...")

# Always render all 5 emoji slots
for i, (emoji, label) in enumerate(MOODS):
    if mood_locked:
        is_selected = today_mood and today_mood["emoji"] == emoji
        # Show styled markdown div
        st.markdown(f"<div style='border:1px solid {'#c06a8b' if is_selected else '#2a3a5a'};"
                    f"opacity:{'1' if is_selected else '0.3'};'>{emoji}</div>")
    else:
        if st.button(emoji, key=f"mood_{i}", help=label, use_container_width=True):
            safe(save_mood, None, username, emoji, label)
            st.rerun()            # Rerun to show locked state
```

Key UX: When mood is locked, all 5 emoji slots stay visible but as styled markdown divs (non-interactive). The selected one has a rose-mauve border, the others are dimmed. When unlocked, all are clickable buttons.

**Journal form (70-92):**

```python
with st.form("journal_form", clear_on_submit=True):     # Form clears after submit
    raw_text = st.text_area("", placeholder="What's on your mind?", height=200)
    submitted = st.form_submit_button("💾 Save Entry")

if submitted and raw_text.strip():
    with st.spinner("Analyzing your entry..."):
        summary = safe(summarize_journal, "Summary unavailable", raw_text)
    safe(save_journal_entry, None, username, raw_text, summary)
    st.success("Entry saved. Check Past Entries to read the AI summary.")
    # No st.rerun() — success message stays visible
```

`clear_on_submit=True` replaces the old `st.rerun()` pattern. The form clears automatically after save, and the success message stays visible because no rerun is triggered.

---

## `emotion_classifier.py` — GoEmotions TF-IDF (50 lines)

```python
EMOTIONS = [
    "admiration","amusement","anger","annoyance","approval","caring","confusion",
    "curiosity","desire","disappointment","disapproval","disgust","embarrassment",
    "excitement","fear","gratitude","grief","joy","love","nervousness","optimism",
    "pride","realization","relief","remorse","sadness","surprise","neutral",
]
```

### `classify_text(text, threshold=0.2)` — Predict emotions (30-50)

```python
def classify_text(text: str, threshold: float = 0.2) -> str:
    _load()                                              # Load pickle model lazily
    if _pipe is None:                                    # Model file missing
        return ""
    cleaned = re.sub(r"\s+", " ", re.sub(r"[^a-z\s]", " ", str(text).lower())).strip()
    if not cleaned:
        return ""
    probs = _pipe.predict_proba([cleaned])
    labels = [EMOTIONS[i] for i, p in enumerate(probs[0]) if p > threshold]
    if not labels:
        return ""
    if "neutral" in labels and len(labels) > 1:          # Remove neutral if other emotions present
        labels.remove("neutral")
    return ", ".join(labels)                             # "sadness, fear, nervousness"
```

Model is a scikit-learn `Pipeline` with `TfidfVectorizer + LogisticRegression` trained on the GoEmotions dataset. Saved as `software/models/emotion_tfidf.pkl` (~4MB).

**Lazy loading:** The model is loaded only on first call via `_load()`. If the pickle file doesn't exist, `classify_text` returns `""` (no crash).

---

## `styles_.py` — Rose-Mauve Theme (30 lines)

Defines the color palette used across all UI components:

```python
ACCENT = "#c06a8b"           # Rose-mauve accent (buttons, highlights, borders)
ACCENT_LIGHT = "#d487a5"     # Lighter rose (hover states)
ACCENT_DIM = "#9a5070"       # Dimmed rose (secondary elements)
BG_DARK = "#0f1420"          # Page background (very dark navy)
BG_CARD = "#162033"          # Card background (dark slate)
BG_CARD_HOVER = "#1c2845"    # Card hover
TEXT_PRIMARY = "#e0e8f0"     # Primary text (light grey-white)
TEXT_SECONDARY = "#7a8aaa"   # Secondary text (muted blue-grey)
TEXT_DIM = "#5a6a8a"         # Dim text (subtle)
BORDER = "#1e3a5a"           # Subtle borders
BORDER_ACCENT = "#c06a8b"    # Accent borders
```

No blue accent tones — the entire interface uses this warm rose-mauve color family.

---

## `booking_.py` — Session Booking (100 lines)

### Patient booking — Date selection changed (v2→v3)

**Before:** `st.date_input()` with a full interactive calendar grid.
**Now:** `st.selectbox()` dropdown of available dates from the psych's availability:

```python
available_dates = safe(get_psych_availability, [], assigned_psych)
if available_dates:
    sorted_dates = sorted(available_dates)           # Chronological order
    selected_date = st.selectbox("Select Date", sorted_dates)
```

Simplifies the UX — patients pick from pre-defined available dates rather than navigating a calendar.

---

## `crisis_.py` — Crisis Engine (380 lines)

### `resolve_crisis(psych_username)` — New function (v3)

```python
def resolve_crisis(psych_username: str):
    """Force-resolve an active crisis without the full acknowledge flow.
    Used for admin cleanup (e.g., wiping stale crisis data after DB purge)."""
    with get_db() as db:
        db.execute("UPDATE crisis_state SET active=0, acknowledged=1, acknowledged_by=?, acknowledged_at=datetime('now')", (psych_username,))
        db.execute("INSERT INTO crisis_log (...) VALUES (...)", {"event": "resolved", ...})
```

### `trigger_crisis(patient)` — Start a crisis (unchanged core)

Writes to `crisis_state` table instead of JSON file:
```python
db.execute("UPDATE crisis_state SET active=1, patient=?, triggered_at=datetime('now'), ...", (patient,))
# Only one active crisis at a time — the table has a single row
```

---

## `followup_.py` — Follow-Up Tasks (220 lines)

### Psychologist view — Filtered by assignment (v2→v3)

**Before:** `get_all_patients()` — showed ALL patients in the system.
**Now:** `get_assigned_patients(psych_username)` — shows only assigned patients:

```python
from patient_profiles_ import get_assigned_patients
patients = get_assigned_patients(psychologist_username) or [...]
```

---

## `psych_export_.py` — Export Center (100 lines)

### Export scope — Scoped to assigned patients (v2→v3)

**Before:** `get_all_patients()` — exported ALL patient data.
**Now:** `get_assigned_patients(username)` — only assigned patients:

```python
from patient_profiles_ import get_assigned_patients
patient_usernames = _safe(get_assigned_patients, [], username)
```

---

## `agent_.py` — AI Agent Functions (unchanged core, 440 lines)

14 functions following the same contract:

1. Gather patient data (journals, grades, bookings)
2. Build prompt with gathered data
3. Call `_query_ai()` → Ollama → Groq → fallback
4. Return dict with `source="ai"` or `source="rule"` + `suggestion`

Key functions:
- `triage_summary(patient)` — Priority + clinical reasoning
- `suggest_slots(patient, psych)` — Suggested time slots
- `draft_followup(patient, psych)` — Draft tasks
- `journal_to_note(patient, journal_text)` — Journal → OAP format
- `mood_trend(patient)` — Word-list sentiment analysis
- `relapse_indicators(patient)` — Trigger word detection
- `pre_session_brief(patient)` — 3-line clinical brief
- `cross_patient_patterns()` — Shared themes across all patients

---

## `ring_.py` — Biometric Emulator (unchanged, 47 lines)

Seeded random number generation:

```python
def get_ring_data(username: str, intensity: float = 1.0):
    seed = hash(username + datetime.now().strftime("%Y%m%d%H")) % (2**31)
    rng = random.Random(seed)
    bpm = int(72 * (0.9 + 0.2 * intensity))          # 64-80 scaled by intensity
    stress = min(100, max(5, int(rng.gauss(35, 15) * intensity)))
    sleep = round(max(3, min(10, rng.gauss(7, 1.2))), 1)
    mood = rng.choices(mood_options, weights=weights, k=1)[0]
```

Stable per user per hour — same username + hour always produces the same vitals.

---

## `smart_room_.py` — Ambient Display (unchanged, 77 lines)

Pure visual rendering: golden circle (calm mode) or blue concentric circles + EEG bars (intense mode).
`intensity` parameter controls glow radius and opacity.

---

## Data Flow Summary

### Journal Save Flow
```
User writes text → Save button
  → AI summary with emotion_classifier hint (patient mode)
  → encrypt_text(raw_content)
  → INSERT INTO journal_entries
  → st.success("Entry saved")
  → Form clears (clear_on_submit=True)
  → No rerun — success message persists
```

### Mood Lock Flow
```
Page load → get_today_mood(username)
  → Returns {emoji, label} if mood set today
  → Returns None if not set

If None:      Show 5 clickable emoji buttons
              Click → save_mood() → st.rerun() → locked state
If has value: Show 5 styled markdown divs, selected highlighted
              All non-interactive until next day
```

### AI Call Chain
```
summarize_journal(text, mode)
  → Cache check (LRU, 20 entries)
  → _get_emotion_labels(text) → emotion_hint
  → Build mode-specific prompt
  → _query_ollama(prompt, timeout=15)   [local, 15s timeout]
    → If result + not echo: use it
  → _query_groq(prompt)                  [Groq Cloud, 30s timeout]
    → If result + not echo: use it
  → _fallback_summary(text, emotions, mode)  [No AI needed]
  → Cache result
  → Return summary
```

### DB Schema Timeline
```
init_db() runs on every app start:
  → CREATE TABLE IF NOT EXISTS for all 15 tables
  → Seed clinic_codes (5 reusable codes)
  → Seed profession_codes (7 codes, one-time use)
  → Seed test accounts (20 patients + 5 psychs + 5 extra)
```

---

## Palette Reference

All UI colors in `styles_.py`:

| Token | Hex | Usage |
|-------|-----|-------|
| `ACCENT` | `#c06a8b` | Primary buttons, highlights |
| `ACCENT_LIGHT` | `#d487a5` | Hover states |
| `ACCENT_DIM` | `#9a5070` | Secondary elements |
| `BG_DARK` | `#0f1420` | Page background |
| `BG_CARD` | `#162033` | Card backgrounds |
| `TEXT_PRIMARY` | `#e0e8f0` | Main text |
| `TEXT_SECONDARY` | `#7a8aaa` | Secondary text |
| `BORDER` | `#1e3a5a` | Element borders |

---

## Account System

### User Types
- **Patient:** Has journal, mood, booking, follow-ups, crisis trigger. Assigned to one psychologist.
- **Psychologist:** Sees only assigned patients. Has triage, notes, booking queue, follow-ups, export.

### Registration Flow
1. Patient enters clinic code → validates against `clinic_codes` table
2. Selects a psychologist from dropdown → `get_clinic_psychs_for_registration(code)`
3. Creates account → `INSERT INTO patient_profiles`
4. Psychologist enters clinic code + profession code → validates both
5. Profession codes are one-time use (set `used=1`); clinic codes are reusable

### Security
- Passwords hashed with PBKDF2-SHA256, 100k iterations
- Journal content encrypted with Fernet symmetric encryption
- `.env` holds API keys and encryption key — excluded from version control

---

*End of per-file code explanation. Covers all v3 changes: SQLite migration, emotion classifier, mood locking, rose-mauve palette, two-mode AI, assigned psych filtering, and reusable clinic codes.*
