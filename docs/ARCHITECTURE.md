# Sentinel — Architecture Reference

This document records module ownership so every file has exactly one home, and every
value has exactly one owner (Constitution #6). A change that needs the same value in two
places is a bug in the architecture, not an opportunity.

## Layering

```
api → services → repositories → models
core   (cross-cutting: config, health, logging, middleware)
ml     (rules + model artifacts: crisis_policy, risk_engine, emotion_classifier, model_registry)
events (publish/subscribe + append-only event store / audit log)
workers (background: ai_worker, notification_worker)
```

Requests flow top-down; no layer reaches across another (a route handler never touches a
model directly — it calls a service or repository).

## Module ownership table

| Concern | Owner (single source of truth) | Consumers |
|---------|-------------------------------|-----------|
| Patient context assembly | `services/patient_context.py` — `recent_patient_context()` + `build_triage_prompt()` | `api/triage.py`, `api/agents.py`, `workers/ai_worker.py` |
| Timeline + change metrics | `services/timeline_service.py` — `build_timeline_events()`, `compute_change_metrics()` | `api/timeline.py`, `api/patients.py` (overview) |
| Event store (audit log) | `events/` subscribers + `services/event_store_service.py` | `api/event_store_api.py` |
| Crisis thresholds & actions | `ml/crisis_policy.py` — frozen `CrisisPolicy` | `workers/ai_worker.py`, `ml/risk_engine.py`, `api/patients.py` |
| Trustee link signing | `core/security.py` — `_make_trustee_link`/`_verify_trustee_link` (HMAC over `patient`+expiry) | crisis emails, `api/crisis.py` public endpoints |
| Risk scoring rules | `ml/risk_engine.py` — `assess_risk_with_explainability()` | `services/ai_service.py`, `workers/ai_worker.py` |
| Emotion model | `ml/emotion_classifier.py` + `ml/model_registry.py` (artifact tracking) | `services/ai_service.py` |
| AI provider boundary | `services/ai_service.py` — `_query_ollama`/`_query_groq`/`_query_ai` | every AI call site |
| Cloud-AI gate | `core/config.py` — `allow_cloud_ai` (default False); Groq no-ops when disabled | `services/ai_service.py` |
| Backup | `scripts/backup_db.py` — snapshot → Fernet → optional S3/AWS4 PUT | ops/deploy |
| Regression gate | `scripts/eval_golden_set.py` — 14-case golden set, `--strict` in CI | `ml/risk_engine.py`, `ml/emotion_classifier.py` |
| Prompt text + versions | the `*_PROMPT_V1` constants (in `ai_service.py` / `api/agents.py` / `services/patient_context.py`) | same file that runs them; persisted as `AIAnalysis.prompt_version` |
| Email/SMTP | `services/notification.py` — `send_email()` | crisis + notification paths |
| Auth + tokens | `core/security.py` | all `api/*` (deps) |
| Config (env) | `core/config.py` — `settings` | everything |
| Health probes | `core/health.py` | `api` health routes, Render `healthCheckPath` |
| Structured logging | `core/logging_config.py` + `core/request_id.py` | whole app |
| Ring/hardware SDK | `services/ring/*` | sensors ingest |

## The central workflow (Constitution #8)

Clinician's consultation is the flow; patient data is organized around the patient but
always serves the clinician:

```
Consultation → Patient Overview (GET /patients/{username}/overview)
            → AI assistance (drafts, triage, briefs — invisible, proposed only)
            → Decision (clinician approves: PUT /psychologists/notes/{id}/approve)
            → Documentation (ClinicalNote with provenance)
            → Follow-up (FollowupTask)
```

The patient dashboard is the patient's surface; the open-session/overview is the
clinician's surface. The overview endpoint composes ~11 sections in one call — the
frontend renders, it does not orchestrate.

## AI provenance chain

Every AI output carries its origin through the whole pipeline:

1. prompt version (`prompt_version`, e.g. `clinical_journal_summary/v1`) — named
   constants, passed to the provider call and persisted on `AIAnalysis`;
2. provider + latency + ok — structured log fields in `services/ai_service.py`;
3. model version + confidence + explanation — stored on `EmotionResult`/`AIAnalysis`/
   `RiskAssessment` and rendered in the overview card;
4. clinician approval — `approved_by`/`approved_at` on `ClinicalNote`/`FollowupTask`.

Nothing AI produces is authoritative until a clinician approves it.

## Deploy-time behavior

- Backend listens on `PORT` (`uvicorn`, Dockerfile default `10000`); frontend nginx
  listens on `PORT` and proxies `/api/` → `BACKEND_URL` server-side (no CORS in prod).
- `/health` = full readiness (DB read + DB write + classifier); `/health/live`,
  `/health/ready`, `/health/ai` exist for finer probes. See `docs/DEPLOYMENT.md`.
- AI unavailability degrades to rule-based output everywhere by contract (see
  Deployment Guide, "Graceful degradation"). Cloud AI (Groq) is additionally gated behind
  `ALLOW_CLOUD_AI=false` by default — an operator opt-in, not an automatic fallback.
