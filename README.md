# Sentinel — AI-Assisted Mental Health Ecosystem

**Continuous mental health infrastructure connecting patients and clinicians through real-time monitoring, AI-powered journal analysis, crisis escalation, and structured follow-up management.**

> **Creator:** Dhansika  
> **Version:** 3.0  
> **Architecture:** SQLite/PostgreSQL · Ollama/Groq AI · Emotion Classifier · Crisis Engine · Rose-Mauve Dark UI

---

## Architecture

```
main_.py                    ← Entry point — login, routing, PWA
│
├── patient_profiles_.py    ← Auth, registration, PBKDF2 hashing
│
├── portal routing (try/except isolated)
│   ├── Patient            → patient_portal_.py  (6 tabs)
│   └── Psychologist       → psychologist_.py    (7 tabs + AI sidebar)
│
├── Core Modules
│   ├── database.py           ← SQLite/PostgreSQL schema + connection pool
│   ├── data_manager_.py      ← All DB operations (journals, notes, bookings, followups, mood)
│   ├── ai_kernel_.py         ← AI: Ollama → Groq → rule fallback, emotion classifier
│   ├── crisis_.py            ← Crisis engine + SMTP email + audio siren
│   ├── agent_.py             ← AI agent functions (triage, slots, patterns, etc.)
│   ├── smart_room_.py        ← Environmental visual simulator
│   ├── ring_.py              ← Seeded biometric data emulator
│   ├── booking_.py           ← Session booking workflow
│   ├── followup_.py          ← Follow-up task engine + grading
│   ├── emotion_classifier.py ← TF-IDF over GoEmotions 28 labels
│   ├── styles_.py            ← Rose-mauve dark palette
│   └── patient_shared_.py    ← Shared utilities
│
└── data/                  ← SQLite database (auto-created, gitignored)
    └── sentinel.db
```

### Fault Isolation

Every module, import, tab, and external call is wrapped in try/except with the `safe(func, default, *args)` pattern. If any single feature crashes, the rest of the app continues with a graceful "unavailable" message.

---

## Features

### Patient Portal (`📊 Wellness · 📝 Journal · 📅 Booking · 📋 Follow-Up · 🧠 Smart Room · 🆘 Emergency`)

| Feature | Description |
|---------|-------------|
| **Biometric Dashboard** | Heart rate, stress, sleep, SpO₂, mood — seeded per user per hour |
| **24h Trend Charts** | Line graphs with table toggle |
| **Wellness Journal** | Free-text → AI summary (empathy mode). Mood emoji locked per day. Raw text encrypted at rest |
| **Session Booking** | Dropdown of available dates from psych's availability |
| **Follow-Up Tasks** | Accept, upload proof, view grades and feedback |
| **Smart Room** | Calm / Intense visual environment |
| **Crisis Trigger** | Emergency siren → timed escalation protocol |

### Psychologist Portal (`📋 Triage · 📝 Notes · 📓 Journal · 📅 Bookings · 📋 Follow-Up · 🧠 Smart Room · 📦 Export`)

| Feature | Description |
|---------|-------------|
| **Patient Triage** | Per-patient expanders with biometric cards, mood charts, crisis auto-expand |
| **Clinical Notes** | Session observations → AI synthesis (OAP format). Journal→Note conversion |
| **Booking Queue** | Accept/waitlist + AI suggest-slots |
| **Follow-Up Grading** | Assign tasks, review proof, grade green/yellow/red |
| **Export Center** | Download patient journal summaries, clinical notes as CSV |
| **AI Agent Sidebar** | Briefs (pre-session brief), Patterns (cross-patient themes), Monitors (silent period, relapse flags) |
| **Crisis Triage** | One-click AI priority summary during active crisis |

### AI Layer

| Component | Description |
|-----------|-------------|
| **Primary** | Local Ollama (`sentinel` model, 7.2B, 4.4GB) |
| **Fallback** | Groq Cloud (`llama-3.1-8b-instant`) — 30s timeout |
| **Fallback 2** | Rule-based extraction (no dependencies) |
| **Emotion Classifier** | TF-IDF + LogisticRegression over 28 GoEmotions labels |
| **Echo Detection** | Prevents AI from echoing raw journal text back as summary |
| **Cache** | 20-entry LRU in session state |
| **Modes** | `patient` (warm reflection, no advice) vs `clinical` (OAP format) |

### Crisis Engine

```
Trigger → 0-29s: Siren → 30s: Email trusted contact → 60s: Helpline escalation
Resolve: Psychologist acknowledges → debrief logged
```

### Biometric Emulation

- `random.Random(username + hour)` — stable per-user, per-hour values
- Metrics: BPM (40-120), Stress (0-100%), Sleep (3-10h), SpO₂ (90-100%)

---

## Database Schema (SQLite)

| Table | Purpose |
|-------|---------|
| `patient_profiles` | Users, passwords (PBKDF2), clinic, assigned psych |
| `clinic_codes` | Reusable clinic registration codes |
| `profession_codes` | One-time psych registration codes |
| `journal_entries` | Encrypted journal text + AI summary per patient |
| `clinical_notes` | Psychologist session notes |
| `bookings` | Session booking requests |
| `psych_availability` | Psychologist available dates |
| `crisis_state` | Active crisis tracking (single row) |
| `crisis_log` | Crisis history timeline |
| `followups` | Follow-up tasks with grades |
| `ring_sessions` | Optional ring session data |
| `ring_sensor_log` | Optional sensor readings |
| `auth_log` | Login attempt history |
| `activity_log` | User activity audit trail |
| `mood_log` | Daily mood entry (one per patient per day) |

---

## Accounts

### Active Users (production)
| Role | Username | Password |
|------|----------|----------|
| Patient | `cel` | `test123` |
| Psychologist | `alaya` | `doc123` |

### Seeded Test Accounts (20 patients, 5 psychs, 5 extra)
All under `CLINIC_ALPHA`. Password for patients: `test123`, psychs: `doc123`, extra: `extra123`.

---

## Installation

```bash
cd sentinel3
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
$env:SENTINEL_DB_BACKEND = "sqlite"
streamlit run software/main_.py
```

See `software/INSTALL.md` for PostgreSQL setup and environment variables.

### Dependencies

```
streamlit>=1.28.0
plotly>=5.17.0
pandas>=2.0.0
numpy>=1.24.0
requests>=2.31.0
cryptography>=41.0.0
python-dotenv>=1.0.0
streamlit-autorefresh>=1.0.0
groq>=1.0.0
```

---

## Testing

```bash
cd software
python -m pytest tests/ -v --tb=short
```

112 tests (79 non-AI + 33 agent tests hitting Groq API).

---

## Data Privacy

- **Journal raw content** encrypted at rest (Fernet). Never shared with psychologist
- **AI summaries** only visible in psychologist portal and exports
- **Clinical vault** segregated per psychologist
- **Mood log** per patient (only today's mood returned, no history leak)
- **`.env`** holds all secrets — excluded from version control

---

## Project Structure

```
sentinel3/
├── software/
│   ├── main_.py                # Entry point
│   ├── patient_portal_.py      # Patient dashboard (6 tabs)
│   ├── psychologist_.py        # Clinician dashboard (7 tabs + AI sidebar)
│   ├── patient_journal_.py     # Journal + mood emoji with per-day lock
│   ├── patient_profiles_.py    # Auth, registration, profile management
│   ├── patient_shared_.py      # Shared UI utilities
│   ├── database.py             # DB schema + connection pool (SQLite/PG)
│   ├── data_manager_.py        # DB operations for all features
│   ├── ai_kernel_.py           # AI router + emotion classifier integration
│   ├── emotion_classifier.py   # TF-IDF over 28 GoEmotions labels
│   ├── crisis_.py              # Crisis engine + SMTP + siren
│   ├── agent_.py               # 14 AI agent functions
│   ├── booking_.py             # Session booking (dropdown calendar)
│   ├── followup_.py            # Follow-up tasks + grading
│   ├── ring_.py                # Seeded biometric emulator
│   ├── smart_room_.py          # Visual smart-room
│   ├── styles_.py              # Rose-mauve dark palette
│   ├── tests/                  # 112 tests
│   ├── models/                 # Trained ML models (emotion_tfidf.pkl)
│   ├── ACCOUNTS.md             # Full account reference
│   └── INSTALL.md              # Detailed install guide
├── scripts/
│   ├── Modelfile               # Ollama model definition
│   ├── fetch_datasets.py       # Dataset download scripts
│   ├── generate_training_data.py
│   ├── sentinel_finetune.ipynb # Training notebook
│   ├── training/               # DistilBERT + TF-IDF trainers
│   ├── dataset_examples/       # Example training datasets
│   └── build_modelfile.py      # Ollama Modelfile builder
├── README.md
├── SENTINEL_CODEBOOK.md        # Per-file code explanation
└── requirements.txt
```

---

## License

Educational project. Built for demonstration of a full-stack healthcare simulation platform.
