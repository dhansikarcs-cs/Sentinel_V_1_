# Sentinel — Engineering Logbook

---

## Pre-Git — Hardware Prototyping

### Late 2025
Started with a dream: build a custom smart ring for emotion detection. Ordered MAX30102 PPG sensors. Prototyped on Arduino Nano. Got heart rate readings after a week of I2C register hacking.

### Early 2026
HRV was a nightmare on raw sensor data. Peak detection, inter-beat intervals, frequency-domain analysis — spent weeks getting a rolling 5-minute HRV window that didn't crash.

### Jan 2026
Designed a custom 2-layer PCB in KiCad 7.0 — nRF52840 BLE + MAX30102, 37 vias. Sent to JLCPCB (¥240, 12-day lead).

**Failure:** PCB arrived. Soldered it. nRF52840 wouldn't flash.
```
JLinkARM.dll: Could not connect to target
```
Root cause: USB D+/D- traces were reversed. Took a week to trace the schematic error.

### Feb 2026
**OEM Pivot:** Did the math. PCB rev2 = ¥240 + 12 days. Enclosure molding = ₹15,000 minimum. Battery certification = months. Time = 3+ months.

Decision: Stop building hardware. Use consumer smart rings (Oura, Ultrahuman, Apple Watch). Sentinel becomes a software platform. Any device exposing HR/HRV via API is compatible.

---

## Phase 1 — Streamlit Prototype

### 2026-03 to 2026-04
Built entire app in Streamlit 1.28. Monolithic architecture:
- `main_.py` (444 lines) — app entry point
- `agent_.py` (720 lines) — AI agent logic
- `database.py` (966 lines) — raw SQLite
- `crisis_.py` — crisis detection with timer
- `patient_portal_.py`, `psychologist_.py` — dual portals
- `ring_.py` — ring data simulator
- `models/emotion_tfidf.pkl` (4 MB) — GoEmotions TF-IDF model

**Bug:** Streamlit single-threaded. `time.sleep(3)` auto-refresh for crisis alerts locked the entire app. Patient typing journal? Frozen.

### 2026-05-12 — First git commit
`5801c0e` — Repository initialized. Dependencies added, .venv removed, Groq API logging fixed.

### 2026-06-09 — 16:45
`e180f34` — V1 ecosystem committed. Patient/psych portals, crisis detection, ring pipeline, AI agents, activity feed, triage, onboarding.

### 2026-06-16
UI sprint — 9 commits:
- Calendar toggle bug (useEffect dependency)
- 3 palette iterations: dusk-slate → rose-mauve → warm neutrals
- 4 agent tests fixed
- Date-picker → dropdown
- Mood per-day fix (UTC vs IST)
- Emoji visibility fix (CSS)

### 2026-06-19 — 21:21
Onboarding flow, assigned psychs, TF-IDF emotion classifier training pipeline.

### 2026-06-20
Docs updated. Proposals finalized. Mood timeline chart + risk badge. Passwords fixed.

---

## Phase 2 — FastAPI + React Rewrite

### 2026-07-15

**06:10 — `14c1a01`**
Complete rewrite:
- Backend: FastAPI 0.109 + SQLAlchemy 2.0 + SQLite/WAL
- Frontend: React 19 + TypeScript 5.4 + Vite 6
- Auth: bcrypt + HS256 JWT + PBKDF2 unlock
- Docker Compose
- Thread-based crisis + WebSocket
- Rule-based discrepancy (18 positive, 22 negative words)
- 3-tier AI: Ollama → Groq → rule fallback
- 45 benchmarks across 5 categories

**06:42 — `dc66736`**
SHA-256 hash-chained audit log with prev_hash.

**07:21 — Docker crash**
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file
```
Fix: mkdir -p in Dockerfile + os.makedirs() in main.py.

**18:51 — `4cd42ec`**
Render deployment. Nginx WebSocket proxy.

**Bug (3 hours):** Nginx strips Upgrade header. Returns HTTP 200 instead of 101.
Fix:
```nginx
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

---

## Phase 3 — Security Hardening

### 2026-07-18 — 05:00
Penetration test — 22 findings: 4 critical, 8 high, 7 medium, 3 low.

### 08:00 – 10:45 — All 22 patched

**A–J (10 original fixes)**
| ID | Finding | Fix |
|----|---------|-----|
| A | WebSocket no auth | get_current_user on WS |
| B | /crisis/* endpoints open | get_current_user on all 3 |
| C | Role escalation | Literal["patient","psychologist"] |
| D | No brute-force | failed_attempts + 15min lockout |
| E | No password policy | min_length=8, max_length=128 |
| F | IDOR | _owns_or_psych() guard |
| G | HMAC timing side-channel | hmac.compare_digest() |
| H | Root containers | USER sentinel in Dockerfiles |
| I | CORS wildcard | Explicit methods/headers |
| J | Default JWT secret | logger.warning() on startup |

**K – HttpOnly Cookie Auth**
JWT was localStorage-only. Set HttpOnly cookie on login (httponly=True, samesite=lax, max_age=28800). get_current_user reads cookie fallback. /auth/logout clears it.

**L – EncryptedText TypeDecorator**
Plaintext DB. EncryptedText(TypeDecorator) — Fernet enc/dec transparent. Applied to 5 fields across 3 models. PBKDF2 600K + HKDF.

**M – RateLimiterMiddleware**
No rate limiting. 100 req/min/IP. /health exempt. 429 + Retry-After.

**N – DOMPurify Sanitization**
Raw text rendered unsanitized. DOMPurify(ALLOWED_TAGS=[], ALLOWED_ATTR=[]) on all text components.

**O – Internal Docker Network**
Backend ports exposed to LAN. Removed ports:, internal: true network. Backend only via Nginx.

**P – Global Exception Handlers**
Stack traces in 500s. Logged server-side. {"detail": "Internal server error"} to client.

**Q – Negation Handling**
"I am not happy" → false positive. 26 negation prefixes + 4-word window stripping. neutral+low_stress no longer alerts.
Accuracy: 92% → 96%. FN: 2 → 0.

**R – Database Backup**
backup_wal() copies .db + .db-wal to data/backups/ on every connection.

**S – Ollama Request Queuing**
Multiple concurrent calls overwhelmed 8GB RAM. threading.Lock + 500ms gap. Rule fallback at 50ms.

### 10:45 — Cleanup
Deleted software/ (59 files, ~10,700 lines Streamlit) → archive/. Removed debug_imports.py.

### Benchmarks
| Metric | Result |
|--------|--------|
| Tests | 43/45 pass |
| Accuracy | 96% (TP:21, TN:27, FP:2, FN:0) |
| SQLite | 48ms |
| Crypto 600K | 233.2ms |

---

## Phase 4 — Documentation

### 2026-07-18 — 10:00 to 10:30

Updated 3 existing docs with all 22 findings:

**TECHNICAL_DESIGN.md** — 14 edits. HttpOnly auth, negation handling, security section expanded 10→22, benchmarks updated.

**JUDGE_QA.md** — 12 new Q&A entries across 6 categories (Encryption, Auth, Rate Limiting, Sanitization, Error Handling, Architecture).

**ENGINEERING_DECISIONS.md** — 12 new rows (31–42) covering every fix.

**Bug found:** Agent wrote rows 31–42 with 5 columns instead of matching the 6-column format. Manually rewrote all 12 rows. Also fixed footer: "10 patches" → "22 patches".

### 10:30 – 11:30 — Logbook + PDF

Created and revised ENGINEERING_LOGBOOK.md multiple times:
- v1: Full narrative → "too casual"
- v2: First-person → "make it specific"
- v3: Timestamps → "include everything from start"

PDF generation — 6 attempts:
| # | Error | Fix |
|---|-------|-----|
| 1 | UnicodeEncodingException (Courier can't render Unicode) | Consolas font |
| 2 | Not enough horizontal space | Explicit set_x(14) |
| 3 | Same on long strings | 120-char pre-wrap |
| 4 | Same after page break | avail < 10 guard |
| 5 | Success — 75 pages | Concise rewrite |
| 6 | Success — 4 pages | Stable |

### 11:30 — Session end

---

## Phase 5 — Crisis Escalation, PWA, Funding & Hardware (M0)

### 2026-07-19 — Crisis escalation + trusted contact portal

- Journal entry with suicidal ideation → classifier (high confidence) → immediate action: suicide hotline card + trusted contacts page exposed on the patient dashboard.
- Trusted contact portal records who is allowed to see an escalation and verifies reachability.
- Real SMTP email sent to the trusted contact (`mom@sentinel.demo`) when a crisis is flagged; demo page set to idle (`active: false`) so no constant beep.
- Crisis for demo patient `alaya` handled end-to-end; trustee portal ADDRESSES gained an alaya entry.

### 2026-07-20 — AI companion mode + PWA

- AI summarization now emits two outputs from the same journal entry: a warm, non-clinical companion summary for the patient and a structured OAP clinical summary for the psychologist.
- Frontend converted to an installable PWA: web manifest, icons, service worker with network-first API caching and stale-while-revalidate assets, offline app shell.

### 2026-07-31 — Funding + hardware

- **Funding:** Emergent Ventures grant received to support hardware procurement and pilot deployment.
- **Hardware:** OEM smart ring sourced from Jport (China); vendor SDK/API + BLE interface (spec sheet pending from Jport).

### 2026-08-03 — Hardware M0: ring ingestion + device binding

Implemented the ring SDK and secured device-binding layer, verified 9/9 SDK tests + end-to-end:

- **Model:** `RingDevice` (`ring_devices` table) — serial, owner patient FK, token_hash (SHA-256), revoked flag, last_seen_at.
- **API:** `POST /ring/pair` (issues one-time device token; re-pairs revoked serials), `POST /ring/unpair`, `GET /ring/devices` (patient or psych), `POST /ring/data` (device-token or patient JWT).
- **Auth:** `get_ring_identity` resolves device serial + token headers (or JWT fallback); constant-time compare, 401 on wrong/unknown/revoked.
- **SDK (`app/services/ring`):** `RingSource` base + canonical `SensorData` payload; `SimulatedRing` (deterministic per-user-per-hour, calm/balanced/stressed), `VendorAPIRingSource` (vendor SDK/cloud `_fetch` hook), `BLEGATTRingSource` (bleak, HRM 0x2A37 parse, battery 0x180F, configurable char maps).
- **Scripts:** `sim_ring.py` (device-token streaming, `--once`), `ring_bridge.py` (any source → `/ring/data`, auto-pair), `test_ring_api.py` (9 tests incl. BLE parsers + missing-bleak guard).
- **Docs:** `docs/ROADMAP_HARDWARE.md` created (M1–M3, Jport spec request sheet, architecture).
- **Demo:** `RING-DEMO-001` paired to `alaya`; verified token-auth pushes (`id=13`, `id=14`) and revocation → re-pair flow.

---

## Final Stack

| Component | Version |
|-----------|---------|
| Python | 3.11 |
| FastAPI | 0.109 |
| SQLAlchemy | 2.0 |
| React | 19 |
| TypeScript | 5.4 |
| Vite | 6 |
| Docker Compose | 2.24 |
| Nginx | 1.25 |
| bleak (bridge-only) | ~0.22 |

## Stats
- Lines: ~25,000
- Commits: 23+
- Security patches: 22 + device-token auth
- Benchmarks: 54 (52 pass; 9 ring API/SDK tests)
- Open TODOs: ~12

---

*Late 2025 → 2026-08-03*
*Sentinel: On-Premises Psychophysiological Triage Node*
*Samsung Solve for Tomorrow · IRIS · ISEF 2026*
