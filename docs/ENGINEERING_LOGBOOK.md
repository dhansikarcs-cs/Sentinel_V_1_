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

## Phase 6 — Red-Team Audit, Trusted-Contact Security & Test Expansion

### 2026-08-04 — Red-team audit (`concerns.md`, gitignored)

Independent audit produced **43 findings** (41 original + 2 added during review): 6 critical,
10 high, 15 medium, 12 low. 8 were directly code-solvable and were implemented in commit
`cc43d0b`; the rest are deployment/misconfiguration items tracked externally (e.g. the Render
dashboard `Sentinel_V_1_` service env).

**Fix 1 (17) — export URL leaked a secret in the query string.**
`?token=` removed from the auth fallback in `core/dependencies.py`; `client.ts` now exports via
`Authorization: Bearer` + blob download (`downloadExport`).

**Fix 2 (32) — cloud AI could fire even when disabled.**
`allow_cloud_ai: bool = False` in `core/config.py`; `_query_groq()` returns early unless enabled.

**Fix 3 (19) — trusted-contact links were plain predictable tokens.**
`_make_trustee_link()` / `_verify_trustee_link()` now use an HMAC over `patient` + expiry
(`SENTINEL_TRUSTEE_LINK_SECRET`, `SENTINEL_TRUSTEE_LINK_EXPIRE_SECONDS`). All crisis emails and
`/public-state`, `/public-trustee-acknowledge`, `/public-trustee-clicked` require a signed link;
`TrusteePortalPage.tsx` renders an invalid-link screen for bad signatures.

**Fix 4 (3) — the AI worker crashed with no evidence when an analysis was skipped.**
Cooldown skip path now emits `journal:summarized` and returns cleanly instead of erroring;
`email_sent` captured on `CrisisLog`; `trigger_cooldown_seconds = 3600` centralized in `crisis_policy.py`.

**Fix 5 (4/34) — AI provenance wasn't visible to patients.**
`AiSourceBadge.tsx` added; rule-mode outputs show "⚠ RULE-SCORED — MODEL OFFLINE"; patient-facing
disclaimers in `JournalPage.tsx` and `Dashboard.tsx`.

**Fix 6 (15) — no automated database backup.**
`scripts/backup_db.py` — consistent SQLite snapshot → Fernet encryption → optional S3-compatible
AWS4-signed PUT (`SENTINEL_BACKUP_KEY`, `S3_*` env vars). Round-trip verified with a throwaway DB.

**Fix 7 (33) — no golden-set regression gate.**
`scripts/eval_golden_set.py` — 14 cases (10 risk bands/triggers + 4 emotion labels), passes
`--strict`; wired into CI so a scoring regression fails the pipeline.

### 2026-08-05 — Test expansion (82 tests) + bugs found

Built a full in-process test harness (`conftest.py`): isolated SQLite DB per run, disabled
rate-limiter + Ollama/Groq + websocket broadcast, seeded user fixtures. New suites:

- `test_risk_engine.py` — band boundaries, emotion contribution, history escalation, explainability
- `test_auth_flow.py` — register/login/refresh, password policy, duplicate/username rules, lockout, role gating
- `test_journal_api.py` — create + background pipeline, idempotency, injection/XSS/blank rejection, soft delete, crisis trigger + cooldown
- `test_export_data.py` — CSV export scoped to assigned patients, role gating
- `test_ring_sensor.py` — pair/token push/unpair/revocation, JWT fallback, range validation
- `test_sync_events.py` — event-store append/replay + API role gating
- `test_model_registry.py` — registry metadata, register/activate, API auth

**Bug found #1 (critical, pre-existing): journal summarization always crashed.**
Both summary prompt templates contained literal `{"summary": "..."}`; Python's `.format()` parsed
the braces as a replacement field → `KeyError: '"summary"'` on **every** journal submission. The
background worker caught it, so entries stayed `ai_source="pending"` forever. Fixed by escaping
braces (`{{"summary": "..."}}`). A regression test locks this down.

**Bug found #2: whitespace-only journal entries were accepted.**
`sanitize_text()` stripped to `""` but `validate_journal_content()` did not reject the result.
Added an explicit empty-content rejection (422).

**Bug found #3: importing `model_registry` mutated `model_registry.json`.**
The module-level `registry.register()` calls always re-wrote the file, bumping `trained_at` and
dirtying the tree on every test run. Registration now preserves the stored `trained_at` and skips
the write when nothing changed.

**Result:** `pytest tests/` = **82 passed**; `ruff check` + `ruff format --check` clean;
`tsc -b` + `vite build` clean; golden set passes `--strict`; `model_registry.json` stays clean.

### 2026-08-05 — Demo review round (risk scale, multi-tab sessions, follow-ups, mood picker)

User feedback from the live demo: "15/10" risk looked broken, two open tabs swapped profiles on
refresh, follow-up interactions needed polish, and the mood picker felt unprofessional.

- **Risk scale integrity:** legacy DB rows held `risk_score` 15/20 (predating the engine's 10-cap).
  The engine's own paths were already `min(10, …)`; now `derive_priorities` and the patient overview
  clamp to `0–10` at read time, and `ai_worker` clamps at write time. Live demo rows normalized to 10.
- **Multi-tab sessions:** auth tokens moved from `localStorage` to `sessionStorage` — each browser
  tab now owns its own session, so patient + psychologist can be open simultaneously and refresh
  keeps the active tab's identity.
- **Follow-ups (both sides):**
  - New `due_date` column (model + schema + API + live DB `ALTER`), overdue/today/upcoming hints.
  - Psychologist: direct **Assign Now** on AI-drafted tasks, **re-grade** anytime, due-date field.
  - Patient: status badges, due-date line, optional proof upload + separate "Mark done"/"Skip".
  - **Authz fix (security):** followup update/upload-proof/download endpoints now enforce ownership
    (patients: their own tasks; psychologists: their own assignments). Also closed a grade-tampering
    hole where a patient could grade their own task — only a psychologist (or `grade=none`) may set it.
- **Mood picker:** shared `MoodPicker` component (Constitution #6), uniform segmented chips with
  mood-color selection states instead of oversized cartoon emojis; kept the once-per-day rule.
  `terrible` emoji 💩 → 😔.

**Result:** 89 backend tests (added `test_followups.py`, risk-clamp case); `ruff`, `tsc`, `vite build`
clean; live demo re-verified end-to-end with Ollama.

### 2026-08-05 — Psych feedback on follow-ups + clinician-friendly Patient Insights

- **Psychologist feedback box:** follow-ups now carry a free-text `feedback` column
  (model `FollowupTask.feedback` as `EncryptedText`, `FollowupUpdate.feedback` max 2000, live DB
  `ALTER`). Psychologist sees a textarea in the grade block, saves without disturbing the grade,
  and the patient sees the note once graded. Non-psychologists cannot write feedback (writes are
  ignored server-side; verified by tests + live tamper check).
- **Patient Insights declutter:** the emotion timeline no longer dumps raw per-entry percentages
  ("they r psych not data analyst na it might be annoying"). The Emotions tab now reads like a
  clinical summary — dominant emotions with avg %, most-consistent emotion, notable rising/receding
  shifts (early-vs-late window), and a light journal timeline with top emotion chips. Raw per-entry
  detail remains in the AI Trace tab. Fixed the Patterns "Top Emotions" bar math (raw 0–1 was shown
  as a percentage).
- **Bug fix: duplicate event-bus subscribers.** The module-level `EventBus` accumulated a fresh copy
  of every subscriber on each app/TestClient lifespan registration, so late-suite tests emitted ~N
  duplicate event-store rows and flooded the `limit=50` read (masking `journal:submitted` with
  `journal:summarized`). `register_all_subscribers` now clears the bus first. Reproducible before,
  green twice after.

**Result:** 93 backend tests (added 4 followup-feedback cases); `ruff`, `tsc`, `vite build` clean;
live demo re-verified (feedback roundtrip, patient tamper ignored, emotion timeline shape).

### 2026-08-05 — Insights speak human, not math ("they r psych not data analyst")

The Patient Insights page was dumping percentages and probability bars to psychologists. Now the
AI eats the raw data and the clinician gets a plain-English note; all the numbers move to one
optional tab at the end.

- **New `GET /patients/{username}/plain-insights`** (psych or the patient themself): gathers the
  same derived facts (mood/engagement trend, top emotions + shifts, risk score, crisis flag, ring
  reading, homework progress) into a compact fact pack, then asks the LLM (Ollama → Groq) to write
  a short update — headline, 3–5 plain insights, and a practical next step. If no model answers,
  a deterministic template writes the same story. Response carries `source`/`provider` so the UI
  shows the rule-fallback badge honestly.
- **Frontend reorganized into two tabs.** "Current State" (default) is human-first: identity line,
  alerts, headline card ("HOW SHE'S DOING"), bulleted insights in plain words, a "WHAT TO DO NEXT"
  card, and the actionable priorities. "Raw Data" (last) holds everything else — the old current-
  state data cards, emotion timeline, AI trace (P=/weight=/contribution=), and patterns — behind an
  explanatory note that it's there for review, not daily use.
- `plain_insights.py` keeps all phrasing logic in one place; risk words mirror the crisis policy
  thresholds (8/7/6/4). LLM output is JSON-parsed defensively and falls back field-by-field.

**Result:** 98 backend tests (added `test_plain_insights.py` — structure, AI path via monkeypatch,
self-access, cross-patient 403, 404); `ruff` + `tsc` + `vite build` clean; live demo shows a real
Ollama-written narrative for alaya.

### 2026-08-05 — Journal→Note with an explicit accept/cancel, and a colour-therapy UI pass

Two follow-ups after the plain-insights demo.

**Journal → Note flow fixed.** Clicking a patient previously dumped the AI draft into the editor
card's "AI draft" box on the far side of the screen with no next step. Now the draft is generated
in-place inside the Journal→Note panel (with journal date, note text, and themes), and the
clinician explicitly chooses **✓ Accept to editor** (fills the note editor, scrolls + focuses it,
shows a "review and Save" confirmation) or **✕ Cancel**. Empty-journal and generation-error states
get their own friendly messages plus a "← Back to patients" reset. The editor's own "AI Draft"
box got the same accept/cancel treatment for consistency.

**Colour therapy ("psych uses this all day").** The cold navy + dusty-mauve palette was swapped for
a restorative sage & earth scheme across all 28 source files (~630 hardcoded tokens, remapped via a
one-shot script — semantic colors for mood/emotion/crisis/OK/amber/danger intentionally untouched):
- Backgrounds: deep green-charcoal (`#151c19`/`#121715`) instead of blue-heavy navy — lower
  blue-light glare, greener = calm/balance/safety.
- Accent: soft sage `#8fcbb1` (healing, growth) replacing dusty mauve `#c49ea4`.
- Text: warm ivory-sage neutrals (`#d9ddd3`, `#f0f2e8`) instead of cool blues — softer on the eye.
- Polish: card shadows + hover lift, `:focus-visible` sage ring, active tab inset glow, softer
  body text rendering, calmer transitions. Alert/priority fills were already neutralized earlier.

**Result:** `tsc` + `vite build` clean; live API smoke test confirms the j2n response shape the UI
renders (`{patient, note, themes}` — 468-char note, themes for alaya); frontend dist rebuilt and
served by the backend.

### 2026-08-05 — Light "therapeutic calm" theme (research-backed, demo-final palette)

The dark sage pass read as "worse than before" in a side-by-side review with a demo two days out, so
it was scrapped and replaced with a light theme grounded in research. Findings that drove the flip
(desktop web searches): desaturated mid-tone blues/teals/greens measurably calm — a Journal of
Environmental Psychology study on color-optimized mental-health settings reported ~35% lower
pre-session anxiety and ~42% better treatment retention; healthcare/therapist dashboards are
overwhelmingly light mode (off-white backgrounds, deep slate text, a single calm teal accent);
light mode wins for daytime professional work (fewer reading errors, better comprehension), and
dark UI causes halation for astigmatism in bright rooms.

**Final palette (Calm Pulse / Calm Sky family):**
- Surfaces: warm-white cards `#FFFFFF`, body gradient `#F4F9F8 → #E8F2F0`, soft surface tints
  `#E3F1EE`/`#F0F7F5`/`#F4F9F8`, borders `#D9E7E3`/`#BFD5CE`.
- Accent: calm teal `#17796E` (primary) / `#3E9C8F` (hover) / `#0E5E55` (deep) — trust + healing.
- Text: deep slate `#3A4F52` body, `#1E3238` headings, `#20363C` strong, `#50695F` labels,
  `#6E837A` muted, `#7C9188` secondary.
- Status kept calm but darkened for light-bg legibility: OK `#2E8B57`, danger `#C7463B`,
  amber `#B7791A`, info `#2E7DB8` — always as tinted-bg banners/chips, never full fills.

**Work done:** one-shot remap script flipped ~29 files (surfaces/text/borders/accent), then a
manual pass fixed every element the token map couldn't reach — hover states that became white-on-
white, steppers/onboarding gradients, calendar availability cells, crisis chips/banners, the
trustee portal, journal expanders, export/consent boxes, tour popover, timeline + recent-activity
rows, inline alert banners, and all leftover `#e0e8f0`-style light-on-dark text (now `#20363C`).
Card shadows softened to teal-tinted instead of pure black.

**Result:** `tsc` + `vite build` clean (690 modules, 8.85 kB CSS / 825 kB JS); backend serving the
light build green at `/` + `/health`; everything verified live as `cel`/`1234`.

### 2026-08-05 — Encoding fix + user-selectable light/dark theme

Two issues from the demo readout.

**Mojibake in Follow-Ups (`ðŸ"‹ My Follow-Up Tasks`).** The emoji in a handful of pages showed as
garbage characters. Root cause: a bulk PowerShell color-edit step read UTF-8 source files as
Windows-1252 (PowerShell 5.1's `Get-Content` default), double-encoding every non-ASCII character in
7 pages (Follow-Ups, Crisis, Export, Trustee Portal, Consultation, Patient Insights, Timeline). Fixed
by reverse-decoding those files through CP1252 back to the original UTF-8 bytes and re-verifying zero
mojibake remains. (Also learned: the token edits themselves turned 8-digit hex alphas like
`#17796E60` into invalid `var(--accent)60` — rewrote those as `color-mix(in srgb, …)`.)

**Light/dark choice instead of a debate.** The app now ships a theme system the user controls, rather
than us picking one palette for them:
- All colors refactored from hardcoded hexes into ~30 CSS custom properties (`--surface`, `--text`,
  `--accent`, `--border`, semantic `--ok/--warn/--danger/--info`, alpha helpers, shadows). ~28 files
  tokenized; the two palettes live in `:root` (light) and `[data-theme="dark"]`.
- Dark palette reuses the proven sage/earth values (`#101714` bg, `#1D2623` surfaces, bright teal
  `#4FBF9F`, warm text `#C9D5D0`); status colors shift to brighter tones for dark-bg contrast.
- `useTheme()` hook (`frontend/src/hooks/useTheme.ts`) + a 🌙/☀️ toggle in the sidebar; choice
  persisted to `localStorage('sentinel-theme')`, defaulting to the OS `prefers-color-scheme`, with a
  pre-paint inline script in `index.html` so there's no theme flash on load.

**Result:** `tsc` + `vite build` clean (691 modules, 11.12 kB CSS / 830 kB JS); live check confirms
correct emoji bytes and both theme blocks in the served bundle.

**Dark-mode polish pass.** User feedback: the gradient was "cool but ruins UI/UX" in dark. Fixed:
- Dark body is now a flat `#101714` (no gradient banding); the subtle light-mode gradient is kept.
- Killed a hardcoded light stop (`#FBFDFC`) in `.card` that turned dark cards two-tone.
- Card elevation in dark now uses real dark shadows (`--shadow`/`--shadow-lg` tokens) instead of
  dark-on-dark teal shadows that made cards invisible against the background.
- Dark borders brightened (`#31423A`) so card edges and dividers read clearly.

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
- Commits: 25+
- Security patches: 22 + device-token auth + 8 red-team fixes (cc43d0b)
- Benchmarks: 54 (52 pass; 9 ring API/SDK tests)
- Backend tests: 89 (pytest) + 14-case golden set (CI-gated)
- Open TODOs: ~12

---

*Late 2025 → 2026-08-05*
*Sentinel: On-Premises Psychophysiological Triage Node*
*Samsung Solve for Tomorrow · IRIS · ISEF 2026*
