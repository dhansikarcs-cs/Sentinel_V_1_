# Sentinel — On-Premises Psychophysiological Triage Node

**Continuous mental health infrastructure connecting patients and clinicians through real-time monitoring, AI-powered journal analysis, crisis escalation, and structured follow-up management.**

> **Stack:** FastAPI + SQLAlchemy (SQLite/PostgreSQL) · React 19 + TypeScript + Vite · Ollama/Groq AI · PWA · Docker Compose · Nginx
> **Status:** Hardware M0 complete (ring SDK + device binding) · Emergent Ventures funded · OEM ring (Jport) in procurement

---

## What Sentinel Does

- **Continuous biometric ingestion** from smart rings (HR, HRV, stress) via a pluggable adapter SDK (`BLE` gateway, vendor cloud, or deterministic simulator)
- **Journal analysis** with AI summaries — a warm companion tone for the patient, a structured OAP clinical summary for the psychologist
- **Discrepancy engine** — rule-based, zero-ML classifier flagging mismatches between subjective journal text and objective physiology
- **Crisis engine** — deterministic escalation (patient → psychologist → trusted contact → helpline) with an active-crisis WebSocket broadcast
- **Clinical workspace** — triage, clinical notes, bookings, follow-up grading, export center
- **Security** — HttpOnly JWT + per-device ring tokens (SHA-256 at rest, constant-time compare), field-level encryption (Fernet), hash-chained audit log, rate limiting

---

## Architecture

```
OEM ring ─┬─ BLE gateway (bleak) ─┐
          ├─ vendor cloud SDK ────┤→ RingSource adapters → SensorData → POST /ring/data
          └─ simulated (dev/test) ┘                                    │
                                                     get_ring_identity (device token)
                                                                      ↓
Frontend (PWA) ── Nginx ── FastAPI API ── SQLite/PostgreSQL
                       │        └─ Ollama (local) → Groq (cloud) → rule fallback
                       └─ WebSocket (crisis broadcast)
```

```
sentinel3/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point, middleware, routers
│   │   ├── api/                       # Routers: auth, journal, crisis, ring, triage, ...
│   │   ├── core/                      # Config, DB, security, rate limiting, dependencies
│   │   ├── models/                    # SQLAlchemy models (users, journal, ring_device, ...)
│   │   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── services/                  # ai_service, audit, websocket, search
│   │   │   └── ring/                  # RingSource SDK: base, simulated, ble_gatt, vendor_api
│   │   ├── ml/                        # emotion_classifier, risk_engine, model_registry
│   │   ├── events/                    # Journal events + subscribers (AI, audit, event store)
│   │   ├── workers/                   # AI background worker
│   │   └── repositories/              # Data-access layer
│   ├── benchmarks/                    # IRIS-style benchmark suite
│   ├── alembic/                       # DB migrations
│   └── requirements*.txt
├── frontend/                          # React 19 + TypeScript + Vite + Tailwind (PWA)
│   └── src/{api,components,lib,pages,stores}
├── scripts/                           # ring_bridge, sim_ring, test_ring_api, seeding, ML training
├── ai_service/                        # Separate AI inference service (Docker)
├── docs/                              # Design, decisions, judge Q&A, hardware roadmap
├── generate_paper.py                  # → docs/sentinel_paper.pdf (research paper)
├── generate_docs_pdf.py               # → judge-prep PDFs
├── docker-compose.yml
└── README.md
```

---

## Hardware Ingestion (M0)

| Component | What it does |
|-----------|--------------|
| `POST /ring/pair` | Binds a device serial to the patient, issues a one-time device token |
| `POST /ring/unpair` | Revokes a device; re-pairing issues a fresh token |
| `POST /ring/data` | Authenticated push (device token or patient JWT) → canonical `SensorData` |
| `GET /ring/devices` | Device state for patient or psychologist |
| `RingSource` SDK | `SimulatedRing` (deterministic per-user/hour), `VendorAPIRingSource` (cloud SDK), `BLEGATTRingSource` (bleak, HRM 0x2A37 + battery 0x180F) |
| `scripts/ring_bridge.py` | Polls any adapter and pushes through the authenticated path |
| `scripts/sim_ring.py` | Streams simulated device-token data (`--once` for a single push) |

Tokens are stored as SHA-256 hashes, compared with `hmac.compare_digest`, and honored per-request. See `docs/ROADMAP_HARDWARE.md` for the M1–M3 plan.

---

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-bridge.txt   # only needed for BLE ring bridge
python seed_demo.py                        # seed demo accounts
uvicorn app.main:app --reload --port 8000
```

Health check: `http://localhost:8000/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Full stack (Docker)

```bash
docker compose up --build
```

---

## Testing

```bash
python scripts/test_ring_api.py    # 9 ring SDK/API tests (incl. BLE parsers)
cd backend && python -m pytest     # backend test suite
```

---

## Accounts (demo seed)

| Role | Username | Notes |
|------|----------|-------|
| Patient | `cel` | `123456` |
| Psychologist | `alaya` | `654321` |
| Demo ring | `RING-DEMO-001` | paired to `alaya` (device token via `/ring/pair`) |

---

## Data Privacy & Security

- Journal raw content encrypted at rest (Fernet, key derived via PBKDF2 600K + HKDF)
- Ring tokens hashed at rest, constant-time comparison, per-request revocation
- HttpOnly cookie JWT (8h) + localStorage fallback for programmatic clients
- Hash-chained audit log; rate limiting (100 req/min/IP); internal Docker network; sanitized 500s
- `.env` holds secrets — excluded from version control

---

## Documentation

| Doc | Purpose |
|-----|---------|
| `docs/TECHNICAL_DESIGN.md` | Full architecture, decisions, trade-offs |
| `docs/ENGINEERING_DECISIONS.md` | Every key decision and alternative |
| `docs/ENGINEERING_LOGBOOK.md` | Build narrative with timestamps |
| `docs/JUDGE_QA.md` | Anticipated judge questions + defensible answers |
| `docs/ROADMAP_HARDWARE.md` | Hardware milestones M1–M3 |
| `docs/sentinel_paper.pdf` | Research paper |
| `SENTINEL_CODEBOOK.md` | Per-file code explanation |

---

## License

Educational project. Built for demonstration of a full-stack healthcare simulation platform.
