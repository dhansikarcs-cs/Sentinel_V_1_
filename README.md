# 🧠 Sentinel

**AI-Assisted Mental Health Ecosystem — Dual Portal Healthcare Simulation Platform**

Sentinel is a modular, futuristic mental-health monitoring platform built with Streamlit. It simulates a complete hospital ecosystem with separate patient and clinician portals, real-time biometric tracking (simulated), AI-powered journal analysis, crisis escalation engine, follow-up task system, smart-room simulation, and a full session booking workflow.

> **Creator:** Dhansika  
> **Architecture:** Dual Portal · Cloud AI · Crisis Engine · Biometric Emulation

---

## Architecture Overview

```
main.py
│
├── patient_profiles.py    ← Auth (3 patients, 2 psychologists)
│
├── Role Detection
│   ├── Patient  →  patient_portal.py  (6 tabs)
│   └── Psychologist →  psychologist.py (7 tabs)
│
├── Shared Services
│   ├── crisis.py           ← Crisis escalation + email alerts
│   ├── followup.py         ← Follow-up task assignment + grading
│   ├── ai_kernel.py        ← Groq AI + Ollama fallback
│   ├── data_manager.py     ← JSON persistent storage
│   ├── smart_room.py       ← Environmental visual simulator
│   ├── ring.py             ← Simulated biometric data emulator
│   ├── booking.py          ← Session booking workflow
│   └── pages/trustee.py    ← Standalone trusted contact page
│
└── data/                   ← Auto-initialized storage directory
```

---

## Features

### Patient Portal (`📊 Wellness · 📝 Journal · 📅 Booking · 📋 Follow-Up · 🧠 Smart Room · 🆘 Emergency`)

| Feature | Description |
|---------|-------------|
| **Biometric Dashboard** | Heart rate, stress, sleep, SpO₂, mood — seeded per user, stable across sessions |
| **24h Trend Charts** | Sharp line graphs with table view toggle, zoom/reset via modebar |
| **Wellness Journal** | Free-text entries → AI summarization (Ollama or fallback). Raw content private, summaries only shared |
| **Journal Export** | Download personal journal summaries as CSV |
| **Session Booking** | 3-step form: attendance count → session details → member details |
| **Booking Notification** | Banner alert when psychologist accepts or waitlists a booking |
| **Follow-Up Tasks** | View assigned tasks, upload proof (photo/file), mark ✅/❌, receive grade + feedback |
| **Smart Room** | Visual environment — calm yellow circle or intense blue circle with sound visualization |
| **Crisis Trigger** | Emergency siren with 30s → trusted contact email, 60s → helpline escalation |

### Psychologist Portal (`📋 Triage · 📝 Notes · 📓 Journal · 📅 Bookings · 📋 Follow-Up · 🧠 Smart Room · 📦 Export`)

| Feature | Description |
|---------|-------------|
| **Patient Triage** | Per-patient expanders with biometric cards, mini trend charts with table toggle, AI clinical insights. Crisis patients auto-expand with red border |
| **Clinical Notes** | Write session observations → AI synthesis into structured clinical notes |
| **Practitioner Journal** | Personal wellness journal with BPM/SpO₂ gauges, 7-day dual-axis trend, 24h stress chart |
| **Booking Queue** | Accept/waitlist workflow with status hierarchy |
| **Follow-Up Tasks** | Assign tasks with file attachments, view patient proof, grade (🟢🟡🔴), write feedback |
| **Export Center** | Download patient summaries, clinical notes, or personal journal as CSV |
| **Sidebar Ops** | Daily workload summary, high-risk patient list, rotating wellness quote, demo toggle |

### Follow-Up Task System

```
Psychologist assigns task (+ file) → Patient sees in Follow-Up tab
    → Patient uploads proof + marks ✅  OR  marks ❌ (skipped)
    → Psychologist grades: 🟢 Correct / 🟡 Partial / 🔴 Wrong
    → Psychologist writes feedback (patient can view + download, cannot reply)
```

- Both sides can download: task attachment, proof file, and feedback as `.txt`
- ✅ button disabled until proof file is uploaded
- Card border colors reflect status: 🟠 pending, 🟢 correct, 🟡 partial, 🔴 wrong/not done
- Persistent JSON storage across sessions

### Crisis Engine

```
Trigger → 🔴 Siren (0-29s)
        → 📧 Trusted Contact Email (30s)
        → 🚨 Helpline Escalation Email (60s)
        → ✅ Psychologist Acknowledgment (stops all escalation)
```

- Real SMTP email via Gmail
- 2-stage escalation with one-shot boolean guards
- Dedicated `/trustee` page for trusted contact response
- Trusted contact flow: notified → on the way → psychologist sees status
- Ambulance-style siren audio
- Frozen resolution timer on acknowledge

### AI Layer

- **Primary Engine:** Groq Cloud (`llama3-70b-8192`) — free, no credit card needed
- **Fallback:** Local Ollama (`mistral`) if Groq is unreachable
- **Last Resort:** Rule-based extraction when no AI is available
- **Caching:** LRU cache (last 20 results) stored in session state

### Biometric Emulation

> **Note:** All biometric data is **simulated**, not real patient data.

- `random.Random(username + hour)` — stable per-user, per-hour deterministic values
- Metrics: BPM (40-120), Stress (0-100%), Sleep (3-10h), SpO₂ (90-100%), Mood (7 states)
- Smart-room intensity multiplier affects stress, BPM, mood distribution
- No real hardware or wearable integration

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
- Ollama (optional — for AI summarization with Mistral)

### Setup

```bash
# Clone or navigate to project directory
cd sentinel3

# Install dependencies
pip install -r requirements.txt

# (Optional) Pull Mistral model for AI features
ollama pull mistral
```

### Environment Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env   # Linux/Mac
copy .env.example .env  # Windows
```

Edit `.env` with your details:

| Variable | Required | Description |
|----------|----------|-------------|
| `SENTINEL_EMAIL` | No | Gmail address for crisis alerts |
| `SENTINEL_EMAIL_PASSWORD` | No | Gmail app password |
| `SENTINEL_RECEIVER` | No | Where crisis alerts are sent |
| `GROQ_API_KEY` | No | Free AI key from [console.groq.com](https://console.groq.com/keys) |
| `SENTINEL_ENCRYPTION_KEY` | No | Auto-generated if empty |

> `.env` is in `.gitignore` — your secrets stay local.

```bash
# Run the application
streamlit run main.py
```

### Dependencies

```
streamlit>=1.28.0
plotly>=5.17.0
pandas>=2.0.0
numpy>=1.24.0
requests>=2.31.0
```

---

## Project Structure

```
sentinel3/
├── main.py                # App orchestrator — login, routing, sidebar
├── patient_portal.py      # Patient dashboard (6 tabs)
├── psychologist.py        # Clinician dashboard (7 tabs)
├── crisis.py              # Crisis engine + SMTP email escalation
├── followup.py            # Follow-up task assignment + grading
├── ai_kernel.py           # Groq AI + Ollama fallback
├── data_manager.py        # JSON persistent storage layer
├── ring.py                # Simulated biometric data emulator
├── smart_room.py          # Visual smart-room environment
├── booking.py             # Session booking workflow
├── patient_profiles.py    # Authentication system
├── requirements.txt       # Python dependencies
├── pages/
│   └── trustee.py         # Standalone trusted contact response page
├── icons/
│   └── icon.svg           # PWA app icon
├── manifest.json          # PWA manifest
├── sw.js                  # Service worker for offline/PWA
├── .gitignore             # Git ignore rules
├── .env.example           # Environment variable template (copy to .env)
├── LICENSE                # MIT license
├── README.md              # This file
└── data/                  # Runtime data directory (gitignored)
    ├── bookings.json
    ├── clinical_vault.json
    ├── crisis_state.json
    ├── followups.json
    ├── history_archive.json
    └── patient_profiles.json
```

---

## Data Privacy Architecture

- **Journal raw content** is stored but never shared with the psychologist
- **AI summaries** only are visible in the psychologist portal and exports
- **Clinical vault** is per-psychologist — notes are not shared between clinicians
- **Crisis state** is file-persisted for reliability across page loads

---

## UI Theme

- Dark medical theme: `#0a0e1a` → `#111827` → `#0a1628` gradient
- Plotly charts with transparent backgrounds, sharp lines, modebar controls
- Toggle between graph and table views on all chart sections
- Gradient-bordered metric cards per biometric value
- Crisis escalation banners with color progression (yellow → orange → dark red)

---

## License

Educational project. Built for demonstration of a full-stack healthcare simulation platform.
