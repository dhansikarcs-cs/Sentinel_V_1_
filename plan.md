# SENTINEL — ARCHITECTURE REFINEMENT PLAN

> **Status:** Plan only. No code has been changed.
> **Review basis (2 sources):**
> 1. **Internal verified audit** — a file-by-file exploration of this repo (every finding below cites `path:line` and was read directly). This is the ground truth.
> 2. **External 15-section AI review** — strategic/UX guidance. Where it aligns with verified code it is adopted; where it praised structures that are actually empty or broken (e.g. `app/domains/*`, the event store, repository depth), this plan **corrects** rather than repeats.
>
> **Mandate (from the user):** do NOT change the overall architecture idea or remove real features. Only **remove what is dead** and **add what is missing**. Refine, never redesign.

---

## 0. Sentinel Architecture Constitution

> Added by the user when approving this plan. These 10 principles are the **approval gate for every future PR** — a change that violates one must be argued at the gate, not merged.

1. **Ecosystem, not app** — Sentinel is a product ecosystem. Every feature must serve more than one surface/partner, or it doesn't earn the complexity.
2. **Strengthen the ecosystem** — every change must strengthen the ecosystem, not just the feature it sits in.
3. **Reduce-burden test** — a feature only earns its place if it *reduces the burden* on the person using it.
4. **AI never decides** — AI proposes, recommends, drafts; a clinician decides. No automatic, unsupervised action driven by AI output. (This is exactly why Phase 6 extracts the inline `>=8` auto-activation in `ai_worker.py:132-180` into a reviewed `CrisisPolicy` — and flags it for product confirmation.)
5. **Context is built once** — patient context is assembled in exactly one place and every screen/call consumes that one build (Phase 2's `patient_context.py`).
6. **One source of truth** — every value (triage tier, mood vocabulary, thresholds) lives in exactly one place; the backend derives, the frontend displays (Phases 2/5).
7. **Backend owns workflows** — backend owns business logic and workflow state; frontend renders and collects input only (Phases 4/5).
8. **Consultation is the center** — the dashboard is the patient's surface; the open-session/overview is the clinician's surface (Phase 4/5 navigation).
9. **Survive AI change** — AI is swappable; nothing critical depends on a specific model/provider (in-process provider boundary in `services/ai_service.py`; documented fallbacks in Phase 7).
10. **Complexity grows slower than features** — no new pattern until existing ones are exhausted; every abstraction must remove more complexity than it adds (Rule 6, applied in every phase).

---

## 1. What We Are NOT Doing (Non-Goals)

- ❌ No rewrite, no framework swap (FastAPI / React / SQLAlchemy stay).
- ❌ No microservices. `ai_service/` microservice gets **deleted**, not promoted.
- ❌ No new CQRS / Event Sourcing / DDD — the existing half-built versions get **removed** or **made honest**.
- ❌ No database migration away from SQLite for now.
- ❌ No new clinical features, no new pages, no new AI models.
- ❌ No visible chatbot / visible agents (external review agrees: AI stays invisible).
- ❌ No raw-journal-as-default UX (external review agrees: summaries first).

---

## 2. Guiding Rules (from the master prompt, restated for this plan)

| Rule | Applied as |
|------|-----------|
| Rule 4 — Delete code whenever possible | Phase 1 removes ~25 dead files/methods. Largest clarity win, zero risk. |
| Rule 1 — Existing module over new module | `services/ai_service.py` absorbs context building; `services/notification.py` absorbs SMTP. |
| Rule 9 — Every change cites existing code | Each phase lists the exact `path:line` evidence. |
| Rule 5 — Must reduce coupling/duplication/cognitive load | Each phase states which metric it improves. |
| Rule 6 — No abstractions for future possibilities | We only centralize what is already duplicated today. |
| Workflow principle — Backend owns business logic | Phase 4/5 move triage scoring + insights off the frontend. |

---

## 3. What We Keep (the architecture and philosophy are sound)

- Layered backend: `api → services → repositories → models` + `core` + `ml` + `workers`.
- The clinical workflow spine: Patient → Journal/Mood/Sensor → AI analysis → Booking → Consultation → Notes → Follow-up → Timeline.
- Human-in-the-loop everywhere: AI drafts, psychologist approves.
- Invisible AI: no chatbot, no visible agents.
- Ring/hardware abstraction under `services/ring/*`.
- Models already store AI provenance partially: `EmotionResult.model_version`, `AIAnalysis.model_version`, `RiskAssessment.algorithm_version`, plus `explanation`/`confidence` fields. (External review's "AI versioning" ask is mostly already true — Phase 6 closes the small gaps.)
- Docker + CI already green (`207a36e` → 6/6 jobs).
- Separated `models/` vs `schemas/` (DB ≠ API).

---

## 4. Verified Baseline (as of this plan)

- CI: **green** on `207a36e` (lint, backend-tests, security-scan, frontend-build, docker-build, deploy-placeholder).
- Local `backend/Dockerfile` build + run: `/health` = 200, `emotion_classifier: available` (verified in Docker).
- ⚠️ **Open blocker:** Render deploy of `Sentinel_V_1_` (a manual service, not `render.yaml`) still exits 1. Not caused by code (proven above). Needs the Render build log / service config (Build + Start commands). Tracked in Phase 7.

---

## 5. THE PLAN — 7 Phases

Each phase is an independent commit; each is revertible; order is low-risk → higher-risk.

---

### PHASE 1 — Delete dead scaffolding (Rule 4) ✅ DONE

**Goal:** Remove every file/method with zero importers. Improves *cognitive load, clarity, maintenance cost*.

> **Executed 2026-08-03.** All deletions below are in place; verified via `ruff check` + `ruff format --check` (clean), `python -c "from app.main import app"` (OK), `scripts/test_ring_api.py` (all pass), frontend `tsc --noEmit` + `vite build` (exit 0).

**Backend deletions (verified zero importers):**
| Path | Evidence |
|------|----------|
| `backend/app/domains/*` (6 packages, re-export only) | grep: no importer anywhere |
| `backend/app/core/cqrs.py`, `core/di_container.py` | only reference each other (`di_container.py:35,41-42`) |
| `backend/app/core/ai_queue.py`, `core/object_storage.py`, `core/secrets.py`, `core/permissions.py` | zero importers |
| `backend/app/ml/feature_store.py`, `ml/feature_vector.py`, `ml/ai_client.py` | zero importers; `ai_client.py` is a "removed: dead code" comment |
| `backend/app/events/journal_events.py`, `events/subscribers/ai_subscriber.py` | zero importers |
| `core/security.py:141-155` `compute_hmac`/`verify_hmac` | self-references only |
| `schemas/mood.py:3` `VALID_MOOD_LABELS` | no consumers |
| `input_validator.py` dead funcs (`:71,78,129,144,155`) | only 3 of 8 used |
| `feature_flags.py:43` `is_enabled()` | zero callers (all flags inert) |
| `services/ai_service.py:13` `_ollama_queue` | unused local |
| `search_service.py:68-70` `sync_index` | never called (until Phase 3 wires it) |

**Frontend deletions (verified no importers):**
| Path | Evidence |
|------|----------|
| `frontend/src/lib/offlineSync.ts`, `lib/sanitize.ts`, `lib/utils.ts` | no importer |
| `frontend/src/pages/EmotionTimelinePage.tsx`, `ExplainabilityDashboard.tsx`, `SmartRoomPage.tsx`, `Unlock.tsx` | absent from `App.tsx` routes |
| `App.tsx:26-28` `PATIENT_ONLY`/`PSYCH_ONLY`/`SHARED` | never referenced |

**Orphaned infrastructure:**
- Delete `ai_service/` (code + `Dockerfile` + `ci.yml:84` build step). It does `sys.path.insert(0, "..")` to reach `backend/app/ml`, is absent from `docker-compose.yml`/`render.yaml`, `config.py:22 ai_service_url` has zero users. The in-process `services/ai_service.py` already owns the provider boundary (`_query_ollama`/`_query_groq`).

**Stale scripts:**
- `scripts/seed_demo_data.py` (imports deleted `data_manager_`), `scripts/test_ai.py` (imports `ai_kernel_`), `scripts/training/prepare_journal_data.py` (points at `software/...`).

**Note on `archive/software/`:** legacy copy including a `.env`; do not delete (history), but flag for key rotation and gitignore is already set.

**Migration/Rollback:** one commit per cluster; recoverable from git.
**Risk:** near-zero. **Effort:** trivial.

---

### PHASE 2 — Unify AI context assembly + move triage logic to backend ✅ DONE

**Goal:** Eliminate the largest duplication cluster; backend owns clinical priority. Improves *duplication, coupling, cognitive load, API complexity*.

> **Executed 2026-08-03.** New `backend/app/services/patient_context.py` is now the **single gatekeeper** for single-patient context (Constitution #5/#6): `triage.py`, `agents.py` (triage_summary, draft_followup, pre-session-brief, crisis_debrief), and `ai_worker.py` all consume `recent_patient_context(...)` + `build_triage_prompt(...)`. `triage-summary` now returns server-derived `tier` + `priority_score` + `crisis` (from `CrisisState`); both duplicated frontend tier formulas (`Layout.tsx:96-103`, `PsychTriagePage.tsx:36-43`) deleted. Added `GET /agents/pre-session-brief/{username}` (Phase 4 foundation). Also fixed a latent `NameError` on `triage-summary`'s AI-fallback path (`data` was referenced outside the try). Panel-level analytics (`compliance-radar`, `relapse-indicators`, `silent-period-watch`, `cross-patient-patterns`, `ring-vitals-risk`) remain direct-DB by design — they are aggregate queries over a whole panel, a legitimate exception. Verified: `ruff` clean, app import OK, `test_ring_api.py` pass, frontend `tsc` + `vite build` exit 0, plus a functional builder smoke test against a seeded in-memory DB.

**Verified duplication (the smoking gun):**
- `api/triage.py:25-59` and `api/agents.py:61-95` are a **verbatim duplicate** (same recent-journal/mood/ring query, same prompt string).
- `agents.py` re-assembles patient context 3 more times: `pre_session_brief` (`:278-333`), `draft_followup` (`:197-220`), `crisis_debrief` (`:631-660`).
- `workers/ai_worker.py:28-35` builds yet another "last 10 journals" window.
- Frontend computes the triage tier **twice, verbatim**: `src/components/Layout.tsx:96-103` and `src/pages/PsychTriagePage.tsx:36-43` — while backend `/agents/triage-summary` already exists but returns only raw score.

**Changes:**
1. New `backend/app/services/patient_context.py`: `recent_patient_context(db, username, journal_limit=…)` returning journals, mood, ring, followups, crisis state; plus one `build_triage_prompt(ctx)` constant. `triage.py`, all four `agents.py` handlers, and `ai_worker.py` consume it.
2. `agents.py triage_summary` returns `score + tier + crisis` (derive tier server-side). Delete both frontend formulas.
3. Add `GET /agents/pre-session-brief/{username}` wiring to the new builder (Phase 4's foundation).

**Migration:** add builder → swap call sites one handler at a time → delete duplicated blocks.
**Rollback:** per-handler revert. **Risk:** low (pure extraction). **Effort:** medium.

---

### PHASE 3 — Correctness & drift fixes — ✅ DONE

**Goal:** Make existing mechanisms honest. Improves *maintainability, trust, data quality*.

1. **Event store alignment** (`events/subscribers/event_store_subscriber.py`, `api/event_store_api.py`, `services/event_store_service.py`):
   - Drop subscriptions to events that are **never emitted** (`crisis:triggered`, `crisis:resolved`, `mood:logged`).
   - Fix name mismatch: subscribed `booking:status_changed` vs emitted `booking:status_updated` (`bookings.py:65`).
   - Either implement `replay()` as a real projection or drop it (currently logs only, `event_store_service.py:65-81`).
   - Result: a credible **audit trail**, not fake event sourcing.
2. **`seed_demo.py`** (476 lines): generate rows from model columns (`model.__table__.columns`) instead of hardcoding; fix out-of-range risk scores `random.choice([15,20,10])` at `:410` (risk engine clamps 1-10, `risk_engine.py:147`).
3. **SMTP single owner:** move live `_send_email` (`api/crisis.py:27-58`) into `services/notification.py` (currently dead, `:7-22`); delete the duplicate.
4. **Search freshness:** FTS5 index built once (`search_service.py:19-40`) but AI writes summaries/emotions after insert (`ai_worker.py:66-71`). Add AFTER UPDATE trigger on `journal_entries`, or call the now-wired `sync_index` post-commit.

**Risk:** low-medium. **Effort:** medium.

**Execution notes (committed `refactor(phase3)`):**
- Subscriber list now mirrors actual emissions exactly (13 types). Added 7 emitted-but-unsubscribed events (`journal:summaries_viewed`, `clinical_note:synthesized`, `clinical_note:saved`, `booking:status_updated`, `followup:updated`, `patient:contact_updated`, `patient:onboarding_updated`, `patient:psych_assigned`); dropped 3 never-emitted (`crisis:triggered`, `crisis:resolved`, `mood:logged`).
- Attribution fix: 6 emission sites now pass `patient_username` so `aggregate_id` is the patient (was `""` for `booking:created`, `booking:status_updated`, `followup:created`, `followup:updated`, `clinical_note:saved`, `patient:psych_assigned`). `clinical_note:synthesized` has no patient in scope and stays aggregate_id-less.
- `replay()` kept as a plain read of the append-only store (no projections exist to rebuild; frontend `client.ts:191` calls it). Not fake event sourcing — the store is now a truthful audit log.
- `seed_demo.py`: hardcoded 19-table delete list replaced with `reversed(Base.metadata.sorted_tables)` (FK-safe, auto-covers new tables e.g. `ring_devices`); risk scores `random.choice([15,20,10])` → `random.randint(5,7)`.
- SMTP: `services/notification.py::send_email(to, subject, body)` is now the single owner (kept the richer crisis version incl. `timeout=10`, `SMTPAuthenticationError` hint); dead duplicate deleted; 4 crisis call sites updated.
- Search freshness: `journal_au` AFTER UPDATE trigger (delete-old + insert-new) mirrors `journal_ai`/`journal_ad`; dead `sync_index` removed (triggers now own the index).
- Verified: ruff clean + formatted, app import OK, ring SDK tests pass, FTS update-trigger + dynamic-cleanup + event-store end-to-end smoke tests pass (temp DB), `tsc --noEmit` 0, `vite build` 0.

---

### PHASE 4 — Patient Overview (workflow API) — the external review's #1 ask, and R3

**Goal:** "The UI makes one request; the backend composes the response." Improves *frontend orchestration, API complexity, context switching*.

**Verified problem:** `PatientInsightsPage.tsx` makes up to **12 endpoint calls per patient** and runs an analytics engine in the browser (`PatternsSection:343-386`). The 3-way AI-trace fetch is duplicated (`PatientInsightsPage.tsx:216-219` ≈ `ExplainabilityDashboard.tsx:18-21`); metrics+timeline assembly duplicated (`TimelinePage.tsx:34-38`).

**Change:** one read-only endpoint `GET /patients/{username}/overview` returning:
`patient profile · last appointment · AI clinical brief (latest summary) · homework/follow-up progress · changes-since-last-visit · mood trend · timeline events · recent sensor trends · latest risk + confidence`.

Composed from existing services/repositories **only** (reuses Phase 2 builder). No new data, no PATCH.

**Migration:** ship endpoint → migrate `PatientInsightsPage` first → other pages when useful.
**Rollback:** old per-entity endpoints stay untouched. **Risk:** medium (contract design, read-only). **Effort:** medium.

---

### PHASE 5 — Frontend refinement (shared constants + consultation-centered flow)

**Goal:** Keep pages, kill duplication, make navigation feel like one consultation. Improves *duplication, cognitive load, clinical usability*.

**Verified duplication:**
- 3 divergent mood vocabularies: `JournalPage.tsx:4-12`, `MoodPage.tsx:4-10`, `TimelinePage.tsx:5-6`, `PatientInsightsPage.tsx:5`.
- `sourceColors` AI-badge map ×4: `JournalPage.tsx:84`, `PsychJournalPage.tsx:5`, `ClinicalNotesPage.tsx:44`, `PsychTriagePage.tsx:116`.
- Whole blocks copied: wellness chart `Dashboard.tsx:5-66` ≈ `PsychJournalPage.tsx:7-62`; crisis stage machine `CrisisPage.tsx:83-91` ≈ `Layout.tsx:168-176`; patient `<select>` ×5 pages; identical `formatTime` and "today" computation ~15 sites.
- Raw auth bypasses: `localStorage.getItem('token')` + hand-rolled Bearer at `FollowupsPage.tsx:32-36,141-145`, `PsychOnboardingPage.tsx:205-209` despite `api/client.ts:54`. 13+ raw-path calls despite typed wrappers (`client.ts:109,115,143-145`).

**Changes:**
1. New `src/constants.ts` (mood map, source colors, `formatTime`, today) + shared `PatientSelector` component + `usePatientContext` hook.
2. Route every request through `api/client.ts`; delete manual Bearer code.
3. Post-Phase 4: switch pages to `/patients/{username}/overview` where it reduces calls.
4. Navigation: keep routes; reorder the psych sidebar so "Today's appointments → Open session (overview) → Notes → Follow-up" reads as one workflow. No new pages.

**Risk:** medium (UI churn, but mechanical). **Effort:** medium-large.

---

### PHASE 6 — Provenance, prompts, and explicit AI policy

**Goal:** Make AI assistive-and-traceable; formalize safety. Improves *AI traceability, safety, maintainability*.

1. **Crisis policy object:** currently thresholds + auto-activation are inline in `ai_worker.py` (notify at `>=7` `:121`, **auto-activate crisis at `>=8`** `:132-180`, warn `>=6` `:181`, priority tiers `:84-89`). Extract to a tested `CrisisPolicy` (thresholds + actions in one audited place). Keeps the safety net; makes it reviewable. **Flag for product confirmation** (this is the "AI decides" boundary).
2. **Prompt versioning:** tag each prompt constant (`build_triage_prompt` v1, etc.) and persist the tag in `AIAnalysis.prompt_version` (new nullable column). Aligns with external review's reproducibility ask.
3. **Clinician-approved provenance:** add `approved_by`/`approved_at` nullable columns to `ClinicalNote`/`FollowupTask` so "AI draft vs clinician-approved outcome" is preserved (external review's "knowledge preservation" ask).
4. **Surface confidence/explainability:** fields already stored (`explanation`, `confidence`); render them in the overview card (Phase 4) so every AI statement carries a "Why?".

**Risk:** low-medium. **Effort:** medium.

---

### PHASE 7 — Operations & production maturity (external review's production section)

**Goal:** close the operational gap. Improves *maintainability, reliability, deployability*.

1. **Resolve the Render blocker** (open issue): get `Sentinel_V_1_` build log; correct Build Command to `pip install -r backend/requirements.txt` and Start Command to `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 10000` if it is a native service, or point it at `render.yaml` (`backend/Dockerfile`).
2. **Health checks:** `/health`, `/health/live`, `/health/ready` already exist (`core/health.py`); add AI-provider + DB-write checks; wire into Render `healthCheckPath`.
3. **Observability:** structured JSON logging (request id already in `core/request_id.py`); log AI latency/failures (per-prompt error rate — connects to Phase 6 prompt tags).
4. **Backups & docs:** document sqlite backup path; write `docs/DEPLOYMENT.md` + `docs/ARCHITECTURE.md` (module ownership table).
5. **Graceful degradation:** ensure AI-unavailable paths already fall back (verified: `summarize_journal` rule fallback, `_query_ai` try/except) — document as a contract.

**Risk:** low. **Effort:** medium.

---

## 6. What We Add (complete list — nothing else)

| Add | Phase | Replaces/Feeds |
|-----|-------|----------------|
| `services/patient_context.py` + one triage prompt | 2 | 6 duplicate context builders |
| Server-side triage `tier` in `/agents/triage-summary` | 2 | 2 duplicate frontend formulas |
| `GET /patients/{username}/overview` | 4 | 12+ frontend calls |
| `CrisisPolicy` object | 6 | inline thresholds in `ai_worker.py` |
| `prompt_version`, `approved_by/at` columns | 6 | provenance gap |
| Shared frontend `constants.ts`, `PatientSelector`, `usePatientContext` | 5 | 5 duplicated vocab/select/block sets |

## 7. What We Remove (complete list — see Phase 1 tables)

~25 backend files/methods + ~7 frontend files + `ai_service/` microservice + 3 stale scripts. No live feature is touched.

---

## 8. Success Metrics (from the master prompt)

- Lower coupling: Phases 2, 4, 5.
- Higher cohesion: Phases 1, 2, 3.
- Reduced duplication: Phases 1, 2, 3, 5.
- Clearer ownership: Phases 1, 3, 6.
- Smaller cognitive load: Phases 1, 2, 4, 5.
- Better AI traceability: Phase 6.
- Improved clinical usability: Phases 4, 5, 6.
- Easier maintenance: all.
- Reduced frontend orchestration: Phases 4, 5.

---

## 9. Execution & Approval Gate

- Each phase = one PR-style commit, run: `ruff check backend/`, `ruff format --check backend/`, `python scripts/test_ring_api.py`, frontend `npx tsc --noEmit` + `npm run build`.
- **Gate:** user approves phase-by-phase. This plan file changes only after an approved refactor updates it (iterative re-review rule).
- Phase 1 and Phase 2 are the two highest-value / lowest-risk starts.

---

*Generated as the single decision document for the refinement effort. Code changes begin only after approval.*
