# Sentinel — Per-File Code Explanation

Every function, every block, every key line explained.

---

## `ai_kernel_.py` — AI Engine (133 lines)

### Imports (1-2)
```python
import os                          # Read env vars for API keys
import streamlit as st             # For session_state cache
```

### Constants (4-6)
```python
CACHE_SIZE = 20                    # Max cached AI responses
OLLAMA_URL = "http://localhost:11434/api/generate"  # Local Ollama API
OLLAMA_MODEL = "mistral"           # Model name for Ollama
```

### `_query_groq(prompt)` — Call Groq Cloud AI (9-25)
```python
def _query_groq(prompt: str) -> str:
    key = os.getenv("GROQ_API_KEY", "")     # Read API key from .env
    if not key or key == "gsk_your_key_here":  # No key or placeholder key
        return ""                           # Skip, returns empty string

    try:
        from groq import Groq               # Import Groq SDK (lazy import)
        client = Groq(api_key=key, timeout=3, max_retries=0)  # Create client, 3s timeout, no retries

        resp = client.chat.completions.create(     # Call the API
            model="llama-3.1-8b-instant",          # Model name (was llama3-8b-8192, that one got decommissioned)
            messages=[{"role": "user", "content": prompt}],  # Standard OpenAI-compatible message format
            temperature=0.3,       # Low randomness (0=deterministic, 2=very random)
            max_tokens=512,        # Max response length (about 400 words)
        )
        return resp.choices[0].message.content.strip()  # Extract text from response object

    except Exception as e:         # ANY error: network, auth, model, timeout
        import sys; print(f"[ai_kernel] Groq error: {e}", file=sys.stderr)  # Log to server console
    return ""                      # Return empty on failure
```

### `_query_ollama(prompt)` — Call local Ollama (28-40)
```python
def _query_ollama(prompt: str) -> str:
    try:
        import requests
        resp = requests.post(
            OLLAMA_URL,                      # http://localhost:11434/api/generate
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},  # JSON body
            timeout=3,                       # Fail fast if no Ollama running
        )
        if resp.status_code == 200:          # HTTP OK
            return resp.json().get("response", "").strip()  # Extract from JSON response
    except Exception:                        # Connection refused, timeout, etc.
        pass                                 # Silently ignore (Ollama likely not installed)
    return ""
```

### `_query_ai(prompt)` — Master AI router (43-50)
```python
def _query_ai(prompt: str) -> str:
    result = _query_ollama(prompt)  # Try local Mistral first (fast, free)
    if result:                      # If Ollama returned something
        return result               # Use it, skip Groq
    result = _query_groq(prompt)    # Fallback to Groq Cloud
    if result:                      # If Groq returned something
        return result               # Use it
    return ""                       # Both failed → empty string
```
**Key rule:** Ollama first (free, private), Groq second (needs internet, API key).

### `_check_cache(key)` / `_set_cache(key, value)` — Cache AI results (53-65)
```python
def _check_cache(key: str):                    # Look up cached AI result
    cache = st.session_state.get("ai_cache", {})  # Get cache dict from session state
    return cache.get(key)                      # Return cached value or None

def _set_cache(key: str, value: str):
    if "ai_cache" not in st.session_state:     # Initialize if not exists
        st.session_state.ai_cache = {}
    cache = st.session_state.ai_cache
    cache[key] = value                         # Store result
    if len(cache) > CACHE_SIZE:                # If cache too big (over 20)
        oldest = next(iter(cache))             # Get first key (oldest)
        del cache[oldest]                      # Remove it (LRU-style eviction)
```
Prevents calling AI APIs for the same text twice.

### `summarize_journal(raw_text)` — Summarize patient journal (68-89)
```python
def summarize_journal(raw_text: str) -> str:
    if not raw_text.strip():                    # Empty or whitespace-only
        return "No content to summarize."

    cache_key = f"journal_{hash(raw_text) % 10**8}"  # Unique key from text hash
    cached = _check_cache(cache_key)
    if cached:                                    # If already cached
        return cached                             # Return cached version

    prompt = (                                    # Build AI prompt
        "You are a clinical AI assistant..."
        f"Journal Entry:\n{raw_text}\n\nSummary:"
    )
    result = _query_ai(prompt)                    # Call Ollama→Groq
    if not result:                                # If AI failed
        result = _fallback_summary(raw_text)      # Use rule-based fallback
    _set_cache(cache_key, result)                 # Cache for next time
    return result
```

### `synthesize_clinical_notes(raw_notes)` — Notes → structured (92-113)
Same pattern as `summarize_journal` but with a different prompt asking for Observations/Assessment/Plan format.

### `_fallback_summary(text)` — Rule-based fallback for journal (116-124)
```python
def _fallback_summary(text: str) -> str:
    lines = [l for l in text.split(". ") if l]  # Split into sentences, remove empty
    if len(lines) > 2:
        return (
            "Patient expresses multiple emotional themes. "
            f"Key topics include: {'; '.join(l.strip()[:60] for l in lines[:3])}. "  # First 3 sentences, 60 chars each
            "Recommended: monitor mood trends..."
        )
    return "Patient shared emotional content. Further exploration recommended..."
```
No AI needed — simple sentence extraction.

### `_fallback_synthesis(text)` — Rule-based fallback for notes (127-133)
```python
def _fallback_synthesis(text: str) -> str:
    return (
        "**Observations**: " + text[:200] + ("..." if len(text) > 200 else "") + "\n\n"
        "**Assessment**: Patient appears engaged in therapeutic process.\n\n"
        "**Plan**: Follow-up session recommended..."
    )
```
Takes first 200 chars as Observations, hardcodes Assessment and Plan.

---

## `patient_profiles_.py` — Users & Auth (61 lines)

### Data structure (7-17)
```python
DEFAULT_PROFILES = {
    "patients": {
        "alice": {"password": "pass123", "name": "Alice Chen", "trusted_contact": "alice_contact@example.com"},
        "bob": {...},
        "charlie": {...},
    },
    "psychologists": {
        "dr.sarah": {"password": "doc123", "name": "Dr. Sarah Blake"},
        "dr.james": {...},
    },
}
```
Hardcoded defaults — 3 patients, 2 psychologists.

### `_load_profiles()` — Read JSON or create defaults (20-31)
```python
def _load_profiles():
    if not os.path.exists(PROFILES_PATH):       # If JSON file doesn't exist
        os.makedirs(os.path.dirname(PROFILES_PATH), exist_ok=True)  # Create data/ dir
        with open(PROFILES_PATH, "w") as f:
            json.dump(DEFAULT_PROFILES, f, indent=2)  # Write defaults to file
        return DEFAULT_PROFILES
    try:
        with open(PROFILES_PATH, "r") as f:
            return json.load(f)                  # Read and parse existing file
    except (json.JSONDecodeError, FileNotFoundError):  # Corrupted or missing
        return DEFAULT_PROFILES                  # Fall back to defaults
```

### `authenticate(username, password)` — Login check (33-41)
```python
def authenticate(username: str, password: str):
    profiles = _load_profiles()
    # Check if username is in patients dict AND password matches
    if username in profiles.get("patients", {}):
        if profiles["patients"][username]["password"] == password:
            return "Patient"              # Return role string
    # Same check for psychologists
    if username in profiles.get("psychologists", {}):
        if profiles["psychologists"][username]["password"] == password:
            return "Psychologist"
    return None                           # Wrong username or password
```

### Name getters (44-51)
```python
def get_patient_name(username: str) -> str:
    profiles = _load_profiles()
    # Navigate: profiles → patients → username → name, fallback to username
    return profiles.get("patients", {}).get(username, {}).get("name", username)

def get_psychologist_name(username: str) -> str:
    profiles = _load_profiles()
    return profiles.get("psychologists", {}).get(username, {}).get("name", username)
```
`.get(key, {})` returns empty dict if key missing — prevents KeyError.

### `get_all_patients()` — List all patient usernames (59-61)
```python
def get_all_patients():
    profiles = _load_profiles()
    return list(profiles.get("patients", {}).keys())  # ["alice", "bob", "charlie"]
```

---

## `data_manager_.py` — All File Storage (235 lines)

### File paths (7-14)
```python
DATA_DIR = "data"
HISTORY_ARCHIVE = os.path.join(DATA_DIR, "history_archive.json")  # Patient journals
CLINICAL_VAULT = os.path.join(DATA_DIR, "clinical_vault.json")    # Psychologist notes
BOOKINGS_JSON = os.path.join(DATA_DIR, "bookings.json")           # Booking requests
CRISIS_STATE = os.path.join(DATA_DIR, "crisis_state.json")        # Active crisis
CRISIS_LOG = os.path.join(DATA_DIR, "crisis_log.json")            # Crisis history
FOLLOWUP_JSON = os.path.join(DATA_DIR, "followups.json")          # Follow-up tasks
```

### Encryption (19-43)
```python
def _get_key() -> bytes:
    raw = os.getenv("SENTINEL_ENCRYPTION_KEY")  # Try env var first
    if raw:
        return raw.encode()
    from cryptography.fernet import Fernet
    return Fernet.generate_key()                 # Or generate random key

def encrypt_text(plain: str) -> str:
    f = Fernet(_get_key())
    return f.encrypt(plain.encode()).decode()    # Encrypt bytes → base64 string

def decrypt_text(cipher: str) -> str:
    try:
        f = Fernet(_get_key())
        return f.decrypt(cipher.encode()).decode()  # Reverse
    except Exception:
        return cipher                             # If can't decrypt, return as-is
```
**Note:** If `SENTINEL_ENCRYPTION_KEY` changes, old data becomes undecryptable.

### `_safe_read_json` / `_safe_write_json` — File helpers (52-70)
```python
def _safe_read_json(path, default=None):
    _ensure_dir()                                # Create data/ if missing
    if default is None:                          # Smart defaults based on filename
        default = {} if "vault" in path or "archive" in path else []  # {} for dict files, [] for list files
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default

def _safe_write_json(path, data):
    _ensure_dir()
    tmp = path + ".tmp"                          # Write to temp file first
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)                        # Atomic swap (prevents corruption)
```

### Patient History functions (75-103)
```python
def save_journal_entry(patient: str, raw_content: str, summary: str):
    archive = _safe_read_json(HISTORY_ARCHIVE, {})  # Read existing
    if patient not in archive:
        archive[patient] = []                        # Init if new patient
    archive[patient].append({
        "raw_content": encrypt_text(raw_content),    # Encrypted journal text
        "summary": summary,                          # AI summary (plaintext)
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    _safe_write_json(HISTORY_ARCHIVE, archive)

def get_patient_history(patient: str):
    archive = _safe_read_json(HISTORY_ARCHIVE, {})
    entries = archive.get(patient, [])
    for e in entries:
        e["raw_content"] = decrypt_text(e.get("raw_content", ""))  # Decrypt on read
    return entries
```

### Clinical Vault (108-126)
Same pattern as journal but keyed by psychologist:
```python
def save_clinical_note(psychologist, patient, raw_notes, ai_synthesis):
    vault = _safe_read_json(CLINICAL_VAULT, {})
    vault[psychologist].append({
        "patient": patient, "raw_notes": encrypt_text(raw_notes),
        "ai_synthesis": ai_synthesis, "timestamp": now
    })
```

### Booking functions (131-155)
```python
def save_booking(patient, date, time, session_type, members, contact, explanation):
    bookings = load_bookings()                    # Read existing list
    bookings.append({
        "patient": patient, "date": date, "time": time,
        "session_type": session_type, "members": members,
        "contact": contact, "explanation": explanation,
        "status": "Pending",                      # Default status
    })
    _safe_write_json(BOOKINGS_JSON, bookings)

def update_booking_status(index: int, new_status: str):
    bookings = load_bookings()
    if 0 <= index < len(bookings):                # Bounds check
        bookings[index]["status"] = new_status     # "Accepted" or "Waitlisted"
        _safe_write_json(BOOKINGS_JSON, bookings)
```

### Crisis functions (159-186)
```python
def get_crisis_state() -> dict:
    return _safe_read_json(CRISIS_STATE, {
        "active": False, "patient": "", ...       # Full default state
    })

def set_crisis_state(state: dict):
    _safe_write_json(CRISIS_STATE, state)
```

### Follow-up functions (191-235)
```python
def save_followup(patient, psychologist, title, description, file_path=""):
    items = load_followups()
    items.append({
        "id": str(uuid.uuid4())[:8],              # Short unique ID (8 chars)
        "patient": patient, "psychologist": psychologist,
        "title": title, "description": description,
        "file_path": file_path, "status": "pending",
        "proof_file": "", "grade": "none",         # Empty until submitted
        "feedback": "",                            # Empty until graded
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    })

def update_followup_status(followup_id, new_status, proof_file=""):
    items = load_followups()
    for item in items:
        if item["id"] == followup_id:              # Find by ID
            item["status"] = new_status            # "completed" or "not_yet"
            if proof_file:
                item["proof_file"] = proof_file     # Uploaded file path
            break

def update_followup_grade(followup_id, grade, feedback=""):
    items = load_followups()
    for item in items:
        if item["id"] == followup_id:
            item["grade"] = grade                  # "green", "yellow", "red"
            if feedback:
                item["feedback"] = feedback
            break
```

---

## `crisis_.py` — Crisis System (358 lines)

### Constants (21-26)
```python
TRUSTED_CONTACT_DELAY = 30    # Seconds before emailing trusted contact
HELPLINE_DELAY = 60           # Seconds before escalating to helpline
SENDER_EMAIL = os.getenv("SENTINEL_EMAIL", "")         # Gmail address
SENDER_PASSWORD = os.getenv("SENTINEL_EMAIL_PASSWORD", "")  # App password
RECEIVER_EMAIL = os.getenv("SENTINEL_RECEIVER", "")    # Where alerts go
```

### `send_email(subject, body)` — Send alert email (63-83)
```python
def send_email(subject: str, body: str):
    _sender = os.getenv("SENTINEL_EMAIL", "")
    _pw = os.getenv("SENTINEL_EMAIL_PASSWORD", "")
    _receiver = os.getenv("SENTINEL_RECEIVER", "")
    if not _sender or not _pw or not _receiver:   # Missing config
        return False                              # Skip silently

    msg = MIMEMultipart()
    msg["From"] = _sender; msg["To"] = _receiver; msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=5)  # Gmail SMTP
        server.starttls()                         # Encrypt connection
        server.login(_sender, _pw)                # Login with app password
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email failed: {e}")            # Show error in Streamlit UI
        return False
```

### `play_alert()` — Generate audio siren (86-121)
```python
def play_alert():
    # Build a WAV file programmatically — no external files needed
    sample_rate = 8000          # 8000 Hz (low quality, small size)
    duration = 1.5              # 1.5 seconds
    num_samples = int(sample_rate * duration)  # 8000 * 1.5 = 12000 samples

    samples = bytearray()
    for i in range(num_samples):
        t = i / sample_rate                    # Time in seconds
        sweep = 440 + 220 * math.sin(2 * math.pi * 3 * t)  # Frequency sweeps 440→660Hz
        pulse = 0.4 + 0.3 * math.sin(2 * math.pi * 2 * t)  # Volume pulses
        sample = int(pulse * 32767 * math.sin(2 * math.pi * sweep * t))
        samples.extend(struct.pack('<h', sample))  # 16-bit little-endian

    # Wrap in WAV container format
    wav = bytearray()
    wav.extend(b'RIFF')                         # RIFF header
    wav.extend(struct.pack('<I', 36 + data_size))  # File size - 8
    wav.extend(b'WAVE')                         # WAVE identifier
    wav.extend(b'fmt ')
    wav.extend(struct.pack('<I', 16))           # Chunk size (16 for PCM)
    wav.extend(struct.pack('<H', 1))            # Audio format (1=PCM)
    wav.extend(struct.pack('<H', 1))            # Channels (1=mono)
    wav.extend(struct.pack('<I', sample_rate))  # Sample rate
    wav.extend(struct.pack('<I', sample_rate * 2))  # Byte rate
    wav.extend(struct.pack('<H', 2))            # Block align
    wav.extend(struct.pack('<H', 16))           # Bits per sample
    wav.extend(b'data')
    wav.extend(struct.pack('<I', data_size))    # Data chunk size
    wav.extend(data)                            # Audio samples

    audio_b64 = base64.b64encode(bytes(wav)).decode()
    st.markdown(
        f'<audio autoplay loop><source src="data:audio/wav;base64,{audio_b64}"></audio>',
        unsafe_allow_html=True,
    )
```
This is a **self-contained WAV generator** — creates an alarm tone without any sound files.

### `trigger_crisis(patient)` — Start a crisis (124-145)
```python
def trigger_crisis(patient_username: str):
    now = datetime.now().isoformat()            # ISO timestamp: "2026-05-20T19:02:00"
    state = {
        "active": True,                         # Crisis flag
        "patient": patient_username,
        "triggered_at": now,
        "acknowledged": False,                  # Psych hasn't responded yet
        "acknowledged_by": "",
        "acknowledged_at": "",
        "helpline_escalated": False,            # 60s timer not started
        "trusted_contact_notified": False,      # 30s timer not started
        "trustee_acknowledged": False,          # TC hasn't responded
        "trustee_clicked": False,               # TC hasn't opened link
        "tc_ack_emailed": False,                # Prevent duplicate emails
        "helpline_ack_emailed": False,
    }
    _safe(set_crisis_state, None, state)        # Save to disk
    _safe(append_crisis_log, None, {"event": "triggered", ...})  # Log event
    # Update session state so UI reacts immediately
    st.session_state.crisis_active = True
    st.session_state.crisis_acknowledged = False
    st.session_state.trusted_notified = False
    st.session_state.helpline_called = False
```

### `acknowledge_crisis(psych_username)` — Psychologist responds (148-190)
```python
def acknowledge_crisis(psychologist_username: str):
    state = _safe(get_crisis_state, {})
    if not state.get("active"):                 # No active crisis
        return
    # Mark as acknowledged
    state["acknowledged"] = True
    state["acknowledged_by"] = psychologist_username
    state["acknowledged_at"] = datetime.now().isoformat()
    _safe(set_crisis_state, None, state)
    _safe(append_crisis_log, None, {"event": "acknowledged", ...})

    # Send appropriate follow-up email based on escalation state
    patient = state["patient"]
    helpline_was = state.get("helpline_escalated", False)
    was_notified = state.get("trusted_contact_notified", False)

    if helpline_was and not state.get("helpline_ack_emailed"):
        # Helpline was called, now psychologist acked — send update
        send_email(f"⚠️ {display}'s crisis — Psychologist acknowledged (after helpline)", ...)
    elif was_notified and not helpline_was and not state.get("tc_ack_emailed"):
        # TC was notified but helpline wasn't reached — send update
        send_email(f"✅ {display}'s crisis — Psychologist intervened", ...)
```

### `handle_escalation()` — Timer-based escalation engine (269-304)
```python
def handle_escalation():
    state = _safe(get_crisis_state, {})
    if not state.get("active"):                 # No crisis
        return
    if state.get("acknowledged"):               # Already resolved
        return

    triggered = datetime.fromisoformat(state["triggered_at"])
    elapsed = (datetime.now() - triggered).total_seconds()

    # Stage 1: 30 seconds → email trusted contact
    if elapsed >= TRUSTED_CONTACT_DELAY and not state.get("trusted_contact_notified"):
        state["trusted_contact_notified"] = True
        send_email(..., f"Trustee page: {_get_ack_link()}")
        _safe(append_crisis_log, None, {"event": "trustee_notified", ...})

    # Stage 2: 60 seconds → escalate to helpline
    if elapsed >= HELPLINE_DELAY and not state.get("helpline_escalated"):
        state["helpline_escalated"] = True
        send_email("🚨 CRISIS — Helpline contacted", ...)
        _safe(append_crisis_log, None, {"event": "helpline_escalated", ...})
```
Each step has a **guard** (`not state.get("flag")`) so it fires only once.

### `get_crisis_status()` — Determine current stage (227-266)
```python
def get_crisis_status() -> dict:
    state = _safe(get_crisis_state, {})
    if not state.get("active"):
        return {"active": False, "stage": "none"}

    triggered = datetime.fromisoformat(state["triggered_at"])
    elapsed = (datetime.now() - triggered).total_seconds()

    # Priority order (most important first):
    if state.get("acknowledged"):           # 1. Resolved
        stage = "acknowledged"
    elif state.get("trustee_acknowledged"): # 2. TC coming
        stage = "trustee_coming"
    elif state.get("trustee_clicked"):      # 3. TC opened link
        stage = "trustee_clicked"
    elif elapsed >= HELPLINE_DELAY:         # 4. 60s passed
        stage = "helpline_escalated"
    elif elapsed >= TRUSTED_CONTACT_DELAY:  # 5. 30s passed
        stage = "trustee_notified"
    else:                                   # 6. Just triggered
        stage = "triggered"
```

---

## `agent_.py` — AI Agent Functions (436 lines)

### Module-level pattern
```python
try:
    from ai_kernel_ import _query_ai      # Try importing AI engine
except Exception:
    def _query_ai(p): return ""           # If import fails, AI always returns empty
```
If `ai_kernel_.py` can't be imported, ALL agent functions use rule-based fallbacks.

### Helper: `_get_journal_texts(patient)` (8-18)
```python
def _get_journal_texts(patient):
    try:
        from data_manager_ import get_patient_history  # Lazy import
        entries = get_patient_history(patient)          # Get all journal entries
        texts = []
        for e in entries[-7:]:                          # Last 7 entries only
            raw = e.get("raw_content", "")
            texts.append(raw[:300])                     # Truncate to 300 chars
        return texts
    except Exception:
        return []                                        # No data = empty list
```

### `triage_summary(patient)` — Assess patient risk (77-100)
```python
def triage_summary(patient: str) -> dict:
    # Step 1: Gather data
    journals = _get_journal_texts(patient)
    grades = _get_grades(patient)
    missed = _count_missed(patient)
    recent_j_count = len(journals)
    name = _get_patient_name(patient)

    # Step 2: Build prompt
    prompt = (
        f"Patient: {name}. Recent journals: {' | '.join(journals[-3:]) if journals else 'none'}. "
        f"Recent follow-up grades: {grades if grades else 'none'}. "
        f"Missed tasks: {missed}. Journals last 7 days: {recent_j_count}. "
        "Assess priority (low/medium/high) and give a 1-line clinical assessment."
    )
    ai = _query_ai("You are a triage AI. " + prompt)

    # Step 3: AI success → return with source="ai"
    if ai:
        priority = "high" if "high" in ai.lower() else ("medium" if "medium" in ai.lower() else "low")
        return {"suggestion": ai, "priority": priority, "source": "ai"}

    # Step 4: Rule-based fallback → return with source="rule"
    reds = grades.count("red")
    yellows = grades.count("yellow")
    if reds >= 2 or missed >= 3:
        return {"suggestion": f"{name} — High priority...", "priority": "high", "source": "rule"}
    if yellows >= 2 or missed >= 1:
        return {"suggestion": f"{name} — Medium priority...", "priority": "medium", "source": "rule"}
    return {"suggestion": f"{name} — Low priority...", "priority": "low", "source": "rule"}
```
**Pattern:** AI first → if AI returns nothing → rule logic. `source` tells the UI whether content is AI-generated or rule-based.

### `suggest_slots(patient, psych)` — Suggest appointment times (103-135)
```python
def suggest_slots(patient: str, psych_username: str = "dr.sarah") -> dict:
    bookings = _get_bookings(patient)         # Get patient's booking history
    psych_name = _get_psych_name(psych_username)

    # Extract past session times and days
    past_times = [b["time"] for b in bookings if b.get("time")]
    past_days = []
    for b in bookings:
        try:
            d = datetime.strptime(b["date"], "%Y-%m-%d")  # Parse date string
            past_days.append(d.strftime("%A"))             # Get day name (Monday, Tuesday...)
        except Exception:
            pass  # Skip invalid dates

    prompt = (
        f"Patient: {name}. Psychologist: {psych_name}. "
        f"Past session times: {past_times if past_times else 'none'}. "
        f"Past session days: {past_days if past_days else 'none'}. "
        "Suggest 3 ideal 1-hour slots in the next 7 days."
    )
    ai = _query_ai("You are a scheduling AI. " + prompt)
    if ai:
        return {"suggestion": ai, "source": "ai"}

    # Rule fallback: use most common past time/day
    from collections import Counter
    preferred_time = Counter(past_times).most_common(1)[0][0] if past_times else "10:00"
    preferred_day = Counter(past_days).most_common(1)[0][0] if past_days else "Monday"
    return {"suggestion": f"1. Next {preferred_day} at {preferred_time}\n2. Following {preferred_day} at {preferred_time}\n3. Midweek at {(int(preferred_time.split(':')[0]) + 1):02d}:00", "source": "rule"}
```
**Note:** `Counter().most_common(1)[0][0]` — get the most frequent item. This is [([item, count])] so [0] gets the tuple, [0] gets the item.

### `draft_followup(patient, psych)` — Draft follow-up tasks (138-152)
Same pattern. Prompt includes latest clinical note + recent grades.

### `journal_to_note(patient, journal_text)` — Journal → clinical note (155-166)
```python
def journal_to_note(patient: str, journal_text: str) -> dict:
    # Takes journal text, converts to structured note
    prompt = (
        f"Patient: {name}. Journal: {journal_text[:500]}. "  # First 500 chars
        "Write a brief clinical note draft (Observations, Assessment, Plan)."
    )
    ai = _query_ai("You are a clinical documentation AI. " + prompt)
    if ai:
        return {"suggestion": ai, "source": "ai"}

    # Fallback: just wrap the journal text in OAP format
    short = journal_text[:200]
    return {"suggestion": f"**Observations**: {short}...\n**Assessment**: Patient is processing...\n**Plan**: Monitor and discuss...", "source": "rule"}
```

### `after_session_summary(patient, clinical_note)` — Patient-friendly (169-175)
Generates 3-sentence summary for the patient to read.

### `pre_session_brief(patient)` — Quick brief before session (178-203)
Gathers journals, grades, missed tasks, last note into a 3-line brief.

### `mood_trend(patient)` — Keyword-based sentiment (206-229)
```python
def mood_trend(patient: str) -> dict:
    journals = _get_journal_texts(patient)
    name = _get_patient_name(patient)
    if len(journals) < 2:                       # Need at least 2 entries for trend
        return {"flag": False, "message": ""}

    negative_words = ["sad", "anxious", "tired", "hopeless", ...]
    positive_words = ["happy", "good", "better", "calm", ...]
    recent = journals[-3:]                       # Last 3 entries
    older = journals[:-3] if len(journals) > 3 else journals  # Earlier entries

    def sentiment_score(texts):                  # Simple pos/neg word counter
        score = 0
        for t in texts:
            t_lower = t.lower()
            score += sum(-1 for w in negative_words if w in t_lower)  # Each negative = -1
            score += sum(1 for w in positive_words if w in t_lower)   # Each positive = +1
        return score

    recent_score = sentiment_score(recent)
    older_score = sentiment_score(older) if older else 0
    if recent_score - older_score <= -3:         # Drop of 3+ points = declining
        return {"flag": True, "message": f"⚠️ {name} — Mood declining...", "severity": "warning"}
    return {"flag": False, "message": f"✅ {name} — Mood stable."}
```
This is a **word-list approach** — no AI needed. Counts positive and negative words, compares recent vs older entries.

### `compliance_radar(patient)` — Task completion % (232-257)
```python
def compliance_radar(patient: str) -> dict:
    tasks = [t for t in load_followups() if t["patient"] == patient]
    pending = [t for t in tasks if t["status"] == "pending"]
    missed = [t for t in tasks if t["status"] == "not_yet"]
    completed = [t for t in tasks if t["status"] == "completed"]

    total = len(pending) + len(missed) + len(completed)
    compliance = (len(completed) / total * 100) if total > 0 else 100  # Percentage

    if missed:
        flags.append(f"{len(missed)} missed tasks")
    # ...returns flags + compliance %
```

### `relapse_indicators(patient)` — Early warning keywords (301-323)
```python
trigger_words = ["can't sleep", "insomnia", "nightmare", "flashback", "panic",
                 "avoid", "isolate", "withdrawn", "no energy", "self-harm",
                 "suicidal", "hopeless", "worthless"]
for t in journals:                              # Check each journal entry
    for w in trigger_words:
        if w in t_lower:                         # Substring match
            indicators.append(w)

if len(indicators) >= 3:                         # 3+ triggers = warning
    warning = f"⚠️ {name} — {len(indicators)} early warning signs detected..."
elif red_count >= 2:                             # 2+ red grades = warning
    warning = f"⚠️ {name} — {red_count} red-graded tasks."
```

---

## `booking_.py` — Bookings (108 lines)

### `render_booking_form(patient_name)` — Patient booking page (8-76)

Shows current booking status then a multi-step form:
```python
member_count = st.number_input("How many members?", min_value=1, max_value=6, ...)
st.session_state.booking_member_count = member_count  # Persist in session state

with st.form("booking_request_form", clear_on_submit=True):  # Form clears after submit
    date = cols_top[0].date_input("Date")          # Date picker
    time = cols_top[1].time_input("Time")           # Time picker
    session_type = cols_top[2].selectbox("Type", ["Therapy", "Follow-up", ...])

    members = []
    for idx in range(member_count):                # Loop for each attendee
        m_name = c1.text_input(f"Member {idx+1} Full Name", ...)
        m_age = c2.number_input("Age", ...)
        members.append((m_name, m_age))

    if submitted:
        if not contact.strip() or not explanation.strip():  # Validation
            st.error("Please complete the Contact and Context fields.")
        else:
            save_booking(...)                       # Save to JSON
```

### `render_booking_queue()` — Psychologist booking management (79-108)
```python
for index, item in enumerate(bookings):            # Loop with index for update
    status_color = "🟢" if item['status'] == "Accepted" else "🟡" if == "Waitlisted" else "⚪"
    with st.expander(f"{status_color} {item['patient']} — {item['date']} @ {item['time']}"):
        if btn_cols[0].button("Accept", key=f"acc_{index}"):    # Key uses index
            update_booking_status(index, "Accepted")             # Update by index
            st.rerun()
```

---

## `followup_.py` — Follow-Up Tasks (214 lines)

### `render_psychologist_followup(psych_username)` — Psychologist view (29-123)

**Assign new task section:**
```python
with st.expander("➕ Assign New Task", expanded=False):
    sel_patient = st.selectbox("Patient", patients, key="fu_psych_patient")
    if uploaded:                                     # Check if file was uploaded
        file_path = _save_uploaded(uploaded, FOLLOWUP_FILES, f"{sel_patient}_{fu_title[:20]}")
    save_followup(sel_patient, psychologist_username, fu_title or "Untitled", fu_desc, file_path)
```

**View assigned tasks with grading:**
```python
for t in reversed(my_tasks):                         # Newest first
    if t["status"] == "completed" and t["proof_file"]:             # Patient submitted
        if current_grade == "none":                                 # Not yet graded
            if st.button("🟢 Correct", key=f"fu_green_{t['id']}"):  # Grade buttons
                update_followup_grade(t["id"], "green")
        else:
            st.markdown(f"**Grade:** {grade_labels.get(current_grade, '')} *(locked)*")

        fb_locked = current_grade != "none" and bool(current_feedback)  # Once feedback saved
        fb = st.text_area("Feedback", ..., disabled=fb_locked)          # Lock after submit
        if not fb_locked and fb != current_feedback:                    # Auto-save on change
            update_followup_grade(t["id"], current_grade, fb)
```
**Key UX:** Grade buttons only show when `current_grade == "none"`. Feedback locks (`disabled=True`) after grade + feedback saved.

### `render_patient_followup(patient_username)` — Patient view (125-214)
```python
if t["status"] == "pending":                         # Task waiting
    uploaded_proof = st.file_uploader("Upload proof...", ...)
    can_complete = uploaded_proof is not None         # Must upload first
    if st.button("✅", disabled=not can_complete):     # Disabled until upload
        dest = _save_uploaded(uploaded_proof, PROOF_FILES, ...)
        update_followup_status(t["id"], "completed", dest)  # Mark done
```

---

## `ring_.py` — Simulated Biometrics (47 lines)

### `get_ring_data(username, intensity)` — Generate vitals (5-28)
```python
def get_ring_data(username: str, intensity: float = 1.0):
    # Seed uses username + current hour → consistent data per user per hour
    seed = hash(username + datetime.now().strftime("%Y%m%d%H")) % (2**31)
    rng = random.Random(seed)                        # Seeded RNG

    base_bpm = 72 + rng.randint(-8, 8)               # 64-80 base
    bpm = int(base_bpm * (0.9 + 0.2 * intensity))    # Scale by intensity

    stress = min(100, max(5, int(rng.gauss(35, 15) * intensity)))  # Gaussian with clamp
    sleep_hours = round(max(3, min(10, rng.gauss(7, 1.2) - (intensity - 1) * 0.5)), 1)

    mood_options = ["calm", "neutral", "anxious", "sad", "happy", "irritable", "fatigued"]
    weights = [0.2, 0.3, 0.15, 0.1, 0.1, 0.05, 0.1]
    if intensity > 1.3:                              # High intensity → negative moods more likely
        weights = [0.05, 0.15, 0.25, 0.2, 0.02, 0.2, 0.13]
    mood = rng.choices(mood_options, weights=weights, k=1)[0]  # Weighted random selection
```

### `get_seeded_history(username, metric, hours)` — Time series data (31-47)
```python
def get_seeded_history(username: str, metric: str, hours: int = 24):
    base_seed = hash(username) % (2**31)
    base_val = {"bpm": 72, "stress": 35, "sleep": 7, "spo2": 97}.get(metric, 50)
    values = []
    for i in range(hours):
        rng = random.Random(base_seed + i * 1000)   # Different seed per hour
        variation = rng.gauss(0, base_val * 0.12)    # 12% Gaussian noise
        val = max(0, min(100, base_val + variation))  # Clamp to 0-100
        values.append(round(val, 1))
    return values
```

---

## `smart_room_.py` — Ambient Display (77 lines)

### `render_smart_room(mode, intensity)` (4-77)
```python
def render_smart_room(mode: str = "calm", intensity: float = 1.0):
    if mode == "calm":
        # Golden circle with soft glow
        <div style="width:180px;height:180px;border-radius:50%;
                    background: radial-gradient(circle at 35% 35%, #ffd700, #b8860b);
                    box-shadow: 0 0 80px rgba(255,215,0,0.25)">
    else:
        # Blue concentric circles + bars (EEG-like graph)
        <div style="position:relative;display:flex;align-items:center;justify-content:center;">
            <!-- 3 concentric circles with varying opacity -->
            <!-- 8 vertical bars (EEG-like) inside -->
        </div>
```
Purely visual. No functionality. `intensity` controls glow radius and opacity dynamically.

---

## `psychologist_.py` — Psychologist Dashboard (714 lines)

### `_safe(func, default, *args)` — Error wrapper (65-71)
```python
def _safe(func, default=None, *args, **kwargs):
    try:
        if func is not None:                        # Skip if function is None (import failed)
            return func(*args, **kwargs)
    except Exception as e:
        import sys; print(f"[_safe] {func.__name__ if func else 'None'}: {e}", file=sys.stderr)
    return default if default is not None else {}    # Return safe default
```
**Critical pattern:** Prints to stderr (server console) but NEVER crashes the UI. Used ~50 times throughout the file.

### `_ai_card(key, text)` — AI suggestion card (124-153)
```python
def _ai_card(key: str, text: str):
    # Renders a styled card with Accept/Edit/Reject
    st.markdown(f"""<div style="background:#1a1f2e;border:1px solid #3a5a8a;border-radius:10px;...">""", ...)

    _ac, _ec, _rc = st.columns(3)                    # 3 buttons side by side
    with _ac:   # Accept
        if st.button("Accept", key=f"{key}_ac", type="primary"):
            st.session_state.pop(key, None)           # Remove from session state
            st.rerun()
    with _ec:   # Edit
        if st.button("Edit", key=f"{key}_ed"):
            st.session_state[f"{key}_edit"] = True    # Flag: show editor
    with _rc:   # Reject
        if st.button("Reject", key=f"{key}_rj"):
            st.session_state.pop(key, None)           # Remove from session state
            st.rerun()

    # Edit mode — inline text editor
    if st.session_state.get(f"{key}_edit"):
        _ed = st.text_area("Edit", value=text, key=f"{key}_ea", height=100)
        _e1, _e2 = st.columns(2)
        with _e1:
            if st.button("Save", key=f"{key}_sv", type="primary"):
                st.session_state[key] = _ed           # Update with edited text
                st.session_state[f"{key}_edit"] = False
                st.rerun()
        with _e2:
            if st.button("Cancel", key=f"{key}_cn"):
                st.session_state[f"{key}_edit"] = False
                st.rerun()
```

### `render_psychologist_portal()` — Main function (156-714)

**Auto-refresh every 5 seconds:**
```python
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=5000, key="psych_crisis_poll")
```

**Crisis banner (174-235):**
Reads `data/crisis_state.json` directly and shows appropriate UI based on stage + elapsed time:
```python
_cs = _read_crisis_state()
if _cs.get("active"):
    _elapsed = int((datetime.now() - datetime.fromisoformat(_cs["triggered_at"])).total_seconds())
    # ...conditional chain checking acknowledged/trustee/helpline/elapsed
```

**Triage button (238-247):**
```python
if _cs.get("active") and not _cs.get("acknowledged"):
    if st.button("🤖 AI Triage Summary"):
        _tr = triage_summary(_cs["patient"])        # Call AI agent
        if _tr and _tr.get("suggestion"):
            st.info(f"{_c} **AI Triage**: {_tr['suggestion']}")
```

**Agent sidebar (250-306):**
```python
if _refresh:                                        # "Refresh Insights" button
    st.session_state.agent_sidebar_cache = {}       # Clear cache → re-fetch

# Three tabs in sidebar
with tab_p:  # Briefs
    for _ap in _all_patients:
        _key = f"brief_{_ap}"
        # Cache: if not in cache, call AI; if in cache, use cached
        if _key not in st.session_state.agent_sidebar_cache:
            st.session_state.agent_sidebar_cache[_key] = _safe(pre_session_brief, {"suggestion": ""}, _ap)
        ...
```

**7 tabs detailed:**

**Tab 0 — Patient Triage (323-370):**
```python
for patient in pts:
    ring = _safe(get_ring_data, {"bpm":72,...}, patient)      # Simulated vitals
    crisis = _safe(get_crisis_status, {"active":False})
    is_crisis = crisis["active"] and crisis["patient"] == patient
    border = "2px solid #ff4444" if is_crisis else "1px solid rgba(255,255,255,0.1)"
    # Shows 5 metric cards + toggleable chart + AI clinical insight
```

**Tab 1 — Clinical Notes (373-484):**
```python
with _cncol1:  # Left: Write note
    with st.form("clinical_note_form"):
        raw_notes = st.text_area("Session Observations", value=st.session_state.get("cn_draft", ""), ...)
        if st.form_submit_button("Generate & Save Note"):
            synthesis = synthesize_clinical_notes(raw_notes)    # AI synthesis
            save_clinical_note(username, sel, raw_notes, synthesis)
            st.session_state["cn_draft"] = ""                   # Clear after save
            st.rerun()

with _cncol2:  # Right: AI draft from journal
    if st.checkbox("Demo?"):                                    # Demo mode
        _cn_demo = _demos_cn.get(_cnjpat, "Standard clinical note.")
        # Shows card with Accept→Editor / Edit / Reject
    if st.button("🤖 Draft Clinical Note"):
        _j2n = journal_to_note(_cnjpat, _cnj_last)              # Call AI agent
        if _j2n and _j2n.get("suggestion"):
            st.session_state["cn_card"] = _j2n["suggestion"]     # Store in session state
        st.rerun()
    if st.session_state.get("cn_card"):                          # Card persisted
        # Shows card with Accept→Editor / Edit / Reject
```

**Tab 3 — Bookings (587-607):**
```python
if st.checkbox("Demo?"):
    _ai_card("b_demo", _demos_b.get(_bpat, "Demo slots"))       # Demo card
if st.button("🤖 Suggest Slots"):
    _sl = suggest_slots(_bpat, username)                         # Real AI call
    if _sl and _sl.get("suggestion"):
        st.session_state["b_card"] = _sl["suggestion"]           # Persist in session state
    st.rerun()
if st.session_state.get("b_card"):
    _ai_card("b_card", st.session_state["b_card"])               # Show persisted card
```

**Tab 4 — Follow-Up (610-630):** Same pattern as Bookings with `draft_followup()`.

**Tab 6 — Export Center (649-711):**
Patient selector → shows journal entries + clinical notes with download buttons.

---

## `patient_portal_.py` — Patient Dashboard (340 lines)

### `render_patient_portal()` (103-340)

**Crisis banner (111-170):**
```python
crisis = _safe(get_crisis_status, {"active": False})
if crisis["active"] and crisis["patient"] == username:
    st_autorefresh(interval=5000, key="crisis_patient_poll")   # Poll during crisis
    # Shows stage progress bar with colored blocks
    stages = [("triggered", "🚨 Triggered", 0),
              ("trustee_notified", "👤 Trusted Contact", 30),
              ("helpline_escalated", "🏥 Helpline", 60)]
    for key, label, sec in stages:
        active = key == stage
        passed = elapsed >= sec
        # Color: red if active, green if passed, dark if not reached
```

**Booking notification (174-190):**
```python
if latest["status"] in ("Accepted", "Waitlisted") and prev_status != latest["status"]:
    st.success("✅ Booking Accepted!")                            # One-time notification
    st.session_state.booking_notified[str(idx)] = latest["status"]  # Prevent repeat
```

**6 tabs:**
```python
tabs = st.tabs(["📊 Wellness", "📝 Journal", "📅 Booking", "📋 Follow-Up", "🧠 Smart Room", "🆘 Emergency"])
```

**Tab 5 — Emergency (320-337):**
```python
if crisis_active:
    st.error("🔴 Siren Active")
    if st.button("Cancel Emergency (False Alarm)"):               # Reset crisis state
        set_crisis_state({"active": False, ...})
else:
    if st.button("🚨 TRIGGER EMERGENCY SIREN", type="primary"):  # Start crisis
        trigger_crisis(username)
```

---

## Data Flow Summary

### AI Call Chain
```
User clicks button
  → agent_ function gathers data
  → _query_ai("prompt")
    → _query_ollama()     [3s timeout, local Mistral]
      → returns text OR empty
    → _query_groq()       [if Ollama failed, 3s timeout]
      → returns text OR empty
    → returns ""          [both failed]
  → if AI return text:    source="ai"
  → if empty:             rule-based fallback, source="rule"
  → result displayed in _ai_card() UI
```

### Crisis Flow
```
Patient triggers siren
  → crisis_state.json: {active: true, patient: "alice", triggered_at: "2026-05-20T19:02:00"}
  → autorefresh detects on every page load (5s)
  → handle_escalation() checks elapsed time:
    0-29s:    Siren active, waiting for psychologist
    30-59s:   Email trusted contact
    60+s:     Email helpline alert
  → Psychologist clicks Acknowledge:
    → crisis resolved, follow-up emails sent
```

### Data Storage
```
Journal entry:  save → encrypt → history_archive.json[patient][] 
                read → decrypt → display
Clinical note:  save → encrypt → clinical_vault.json[psychologist][]
                read → decrypt → display
Booking:        save → bookings.json[]  →  psychologist accepts/waitlists
Follow-up:      save → followups.json[] → patient submits proof → psychologist grades
Crisis:         save → crisis_state.json (single object) + crisis_log.json (array)
```

---

*End of per-file code explanation. Every function, every block, every pattern explained.*
