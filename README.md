# Sentinel — AI-Assisted Mental Health Ecosystem

**Continuous mental health infrastructure connecting patients, clinicians, and trusted contacts through real-time monitoring, AI-powered triage, automated crisis escalation, and structured follow-up management.**

> **Creator:** Dhansika  
> **Version:** 3.0  
> **Architecture:** Microservice-Isolated Modules · Local/Groq AI · Crisis Engine · Biometric Emulation · PWA

---

## Architecture

```
main_.py                  ← Entry point — login, routing, PWA, trustee portal
│
├── patient_profiles_.py  ← Auth (3 patients, 2 psychologists)
│
├── portal routing (try/except isolated)
│   ├── Patient       →  patient_portal_.py   (6 tabs)
│   └── Psychologist  →  psychologist_.py     (7 tabs + AI sidebar)
│
├── Shared Modules (fault-isolated — one failure never affects others)
│   ├── crisis_.py         ← Crisis engine + SMTP email + audio siren
│   ├── ai_kernel_.py      ← AI: Groq Cloud → Ollama → rule-based fallback
│   ├── data_manager_.py   ← JSON persistent storage + encryption
│   ├── agent_.py          ← 14 AI agent functions (triage, slots, patterns, etc.)
│   ├── smart_room_.py     ← Environmental visual simulator
│   ├── ring_.py           ← Seeded biometric data emulator
│   ├── booking_.py        ← Session booking workflow
│   └── followup_.py       ← Follow-up task engine + grading
│
└── data/                  ← JSON storage directory
    ├── crisis_state.json
    ├── crisis_log.json
    ├── bookings.json
    ├── followups.json
    ├── clinical_vault.json
    ├── history_archive.json
    └── patient_profiles.json
```

### Fault Isolation

Every module, import, tab, and external call is wrapped in try/except with the `_safe(func, default, *args)` pattern. If any single feature crashes — missing dependency, API timeout, file corruption — the error is caught at the boundary and the **rest of the app continues** with a graceful "unavailable" message. A broken `agent_.py` does not block the patient portal. A crashed bookings tab does not block the triage tab. Each feature is its own microservice within a single process.

---

## Features

### Patient Portal (`📊 Wellness · 📝 Journal · 📅 Booking · 📋 Follow-Up · 🧠 Smart Room · 🆘 Emergency`)

| Feature | Description |
|---------|-------------|
| **Biometric Dashboard** | Heart rate, stress, sleep, SpO₂, mood — seeded per user per hour, stable across sessions |
| **24h Trend Charts** | Line graphs with graph/table toggle, zoom/reset |
| **AI-Powered Insights** | Expander shows journal count, compliance %, grade breakdown (green/yellow/red), mood trend direction, relapse flags |
| **Wellness Journal** | Free-text entries → AI summarization (Groq → Ollama → rule). Raw content encrypted at rest, never shared with psychologist |
| **Session Booking** | 3-step form: attendance → session details → member info |
| **Follow-Up Tasks** | Accept, complete with proof upload, view grades and feedback |
| **Smart Room** | Calm (yellow) / Intense (blue) visual environment |
| **Crisis Trigger** | Emergency siren → 3-stage escalation protocol |

### Psychologist Portal (`📋 Triage · 📝 Notes · 📓 Journal · 📅 Bookings · 📋 Follow-Up · 🧠 Smart Room · 📦 Export`)

| Feature | Description |
|---------|-------------|
| **Patient Triage** | Per-patient expanders with biometric cards, mini charts, AI insights. Crisis patients auto-expand with red border |
| **Clinical Notes** | Write session observations → AI synthesis into structured notes (OAP format). Also: Journal → Note conversion from patient entries |
| **After-Session Summary** | One-click AI summary generation from any saved clinical note |
| **Booking Queue** | Accept/waitlist + AI suggest-slots feature |
| **Follow-Up Grading** | Assign tasks, review proof uploads, grade green/yellow/red with feedback |
| **Export Center** | Download patient journal summaries, clinical notes, personal journal as CSV |
| **AI Agent Sidebar** | 3 tabs: Briefs (pre-session brief per patient), Patterns (cross-patient themes + compliance), Monitors (silent period + relapse flags) |
| **Crisis Triage AI** | One-click AI-priority summary during active crisis (🚨/⚠️/ℹ️) |

### AI Agent Functions (`agent_.py`)

All 14 functions follow the same contract: `AI call → rule-based fallback → return dict`. All are **button-triggered suggestions** — AI proposes, psychologist approves/edits/ignores.

| Function | Inputs | Returns |
|----------|--------|---------|
| `triage_summary` | patient | priority (high/medium/low) + clinical reasoning |
| `suggest_slots` | patient, psych | suggested time slots |
| `draft_followup` | patient, psych | draft follow-up tasks |
| `journal_to_note` | patient, journal_text | structured clinical note draft |
| `after_session_summary` | patient, clinical_note | patient-facing session summary |
| `pre_session_brief` | patient | recent journals, grades, mood, compliance, flags |
| `mood_trend` | patient | declining/improving/stable direction |
| `compliance_radar` | patient | compliance % + message |
| `silent_period_watch` | patient | flag if no journal in N days |
| `relapse_indicators` | patient | flag if red flags detected |
| `cross_patient_patterns` | — | shared themes across all patients |
| `patient_insights` | patient | journal_count, compliance, missed, grades |
| `crisis_debrief` | — | structured post-crisis summary |
| `crisis_rules` | config | suggested crisis rule configuration |

### Crisis Engine

```
Trigger
  → 0-29s:     🔴 Siren (440-660Hz sweep, amplitude pulsing)
  → 30s:       📧 Trusted Contact email (with /?trustee=1 link)
  → 30s+:      👤 Banner shows TC status (notified/clicked/en route)
  → 60s:       🚨 Helpline escalation email
  → Acknowledge: ✅ Freezes timer, halts escalation, logs debrief
```

- Real SMTP via Gmail app password
- One-shot boolean guards (no duplicate emails)
- Trustee page at `/?trustee=1` — view crisis, acknowledge arrival
- Crisis log in sidebar — last 5 events with icons
- Auto-generated AI debrief on acknowledgment

### AI Layer

| Component | Description |
|-----------|-------------|
| **Primary** | Groq Cloud free-tier (`llama3-8b-8192`) — sub-second response |
| **Fallback 1** | Local Ollama (`http://localhost:11434`) |
| **Fallback 2** | Rule-based extraction (no dependencies) |
| **Cache** | 20-entry LRU in session state |
| **Functions** | Journal summarization, clinical note synthesis |

### Biometric Emulation

- `random.Random(username + hour)` — stable per-user, per-hour values
- Metrics: BPM (40-120), Stress (0-100%), Sleep (3-10h), SpO₂ (90-100%), Mood (7 states)
- Smart-room intensity multiplier affects stress, BPM, mood distribution

---

## Demo Credentials

| Role | Username | Password |
|------|----------|----------|
| Patient | `alice` | `pass123` |
| Patient | `bob` | `pass123` |
| Patient | `charlie` | `pass123` |
| Psychologist | `dr.sarah` | `doc123` |
| Psychologist | `dr.james` | `doc123` |

---

## Installation

### Prerequisites

- Python 3.9+
- (Optional) Ollama for local AI fallback
- (Optional) Groq API key for cloud AI (set in `.env`)

### Setup

```bash
cd sentinel3
pip install -r requirements.txt
cp .env.example .env    # Add your Groq API key and SMTP credentials
streamlit run main_.py
```

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

## Project Structure

```
sentinel3/
├── main_.py               # Entry point — login, routing, trustee portal, PWA
├── patient_portal_.py     # Patient dashboard (6 tabs + insights)
├── psychologist_.py       # Clinician dashboard (7 tabs + AI sidebar)
├── crisis_.py             # Crisis engine + SMTP + audio siren
├── agent_.py              # 14 AI agent functions
├── ai_kernel_.py          # Groq → Ollama → rule fallback
├── data_manager_.py       # JSON persistence + encryption
├── ring_.py               # Seeded biometric emulator
├── smart_room_.py         # Visual smart-room environment
├── booking_.py            # Booking workflow
├── followup_.py           # Follow-up task engine
├── patient_profiles_.py   # Authentication
├── .env                   # Secrets (Groq key, SMTP, ACK_LINK)
├── requirements.txt
└── data/                  # Runtime data (auto-created)
```

---

## Data Privacy

- **Journal raw content** encrypted at rest (Fernet). Never shared with psychologist
- **AI summaries** only visible in psychologist portal and exports
- **Clinical vault** segregated per psychologist
- **Crisis state** file-persisted for cross-portal synchronization
- **`.env`** holds all secrets — excluded from version control

---

## Deployment

- **Render.com** free tier: HTTPS, auto-deploy from GitHub, ~30s cold start
- **PWA**: "Add to Home Screen" on mobile, offline service worker manifest
- **Configuration**: Environment variables via Render dashboard or `.env`

---

## License

Educational project. Built for demonstration of a full-stack healthcare simulation platform.
