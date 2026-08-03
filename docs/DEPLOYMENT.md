# Sentinel — Deployment Guide

Sentinel deploys to Render via a Docker Blueprint (`render.yaml`). This document is the
operating contract: how it is built, what every environment variable does, and what
degrades gracefully when pieces fail.

## Services

| Service | Render type | Runtime | Docker context | Health check |
|---------|-------------|---------|----------------|--------------|
| `sentinel-backend` | web | docker | `./backend` | `GET /health` |
| `sentinel-frontend` | web | docker | `./frontend` | `GET /` |

Both services run on Render's injected `PORT` (default `10000`). Neither assumes the old
hardcoded `8000`.

### Backend

`backend/Dockerfile` runs `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}`.
Render routes its health probe to `/health`, which returns:

- `status: healthy` only when the SQLite **read** and **write** checks pass and the local
  emotion classifier is loadable;
- `status: degraded` when the DB is up but no AI provider answers — the service stays
  available, because every AI call already has a rule-based fallback (see Graceful
  Degradation).

### Frontend

`frontend/Dockerfile` builds the Vite app, then serves it with nginx. `nginx.conf` is an
[envsubst template](https://hub.docker.com/_/nginx) copied to
`/etc/nginx/templates/default.conf.template`, so the container entrypoint substitutes
real values at boot:

| Variable | Meaning | Required |
|----------|---------|----------|
| `PORT` | nginx listen port (Render injects it) | yes |
| `BACKEND_URL` | base URL the SPA's `/api/*` calls are proxied to | yes |

Because nginx proxies `/api/` to `BACKEND_URL` server-side, the browser never talks
cross-origin and CORS is irrelevant in production. The proxy keeps the `/api/` prefix
strip (backend routes are `/api/...`) and forwards `Upgrade`/`Connection` headers for
WebSocket/SSE endpoints.

Set `BACKEND_URL` to `https://sentinel-backend.onrender.com` (public) or the internal
`http://sentinel-backend:10000` (same-account, faster).

## Environment variables (backend)

| Variable | Default | Notes |
|----------|---------|-------|
| `DATABASE_URL` | `sqlite:///./data/sentinel.db` | relative to the `backend/` working dir |
| `JWT_SECRET` | `change-me-in-production...` | **must** be overridden in prod (`generateValue` in `render.yaml`) |
| `CORS_ORIGINS` | `http://localhost:5173` | comma-separated; local dev only — prod proxies via nginx |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | dev default for Docker Desktop; set `http://localhost:11434` for native runs |
| `OLLAMA_MODEL` | `sentinel` | model name Ollama loads |
| `GROQ_API_KEY` | unset | fallback provider; empty → Groq path skipped |
| `SMTP_HOST/PORT/USER/PASSWORD` | gmail defaults | for crisis notifications; unset → email disabled (logs only) |
| `EMAIL_FROM`, `HELPLINE_EMAIL` | — | sender + helpline contact |
| `LOG_FORMAT` | `json` | `json` = one JSON object per line; `text` = human-readable |

All settings are read in `backend/app/core/config.py` (`pydantic-settings`, env file
`../.env` for local dev).

## SQLite storage — important caveat

`DATABASE_URL` points at a SQLite file under `backend/data/`. Render's free/starter plans
have an **ephemeral filesystem**: the file is recreated on each deploy and not shared
across instances. For a real deployment, either:

1. attach a Render **Disk** to `sentinel-backend` and set
   `DATABASE_URL=sqlite:////var/data/sentinel.db`; or
2. swap to a managed Postgres later (the data layer already goes through SQLAlchemy;
   only the `PRAGMA user_version` write-probe in `core/health.py` is SQLite-specific).

**Backup path (local/native):** `backend/data/sentinel.db` (plus `-wal`/`-shm` if WAL is
on). Stop the process, then copy all three files.

## Observability

Every request gets an `X-Request-ID` (echoed on the response) and logs a structured
`request_start` line. With `LOG_FORMAT=json` each line is a JSON object with `ts`, `level`,
`logger`, `message`, `request_id`, plus `provider`, `latency_ms`, `ok`, `prompt_version`
fields on AI calls (see `core/logging_config.py`, `core/request_id.py`,
`services/ai_service.py`).

Stream Render logs to a metrics store and alert on:

- `ai_request` with `"ok": false` (rate = per-provider error rate);
- `health_full.status != healthy` (readiness probe failure).

## Graceful degradation (contract)

AI is a proposed layer, never a dependency:

1. **Ollama down** → `_query_ollama` returns `None`; the Groq fallback runs.
2. **Both AI providers down** → `summarize_journal` and `synthesize_clinical_notes`
   return rule-based summaries; agent handlers return deterministic defaults
   (`json.loads` falls back to preset JSON). All responses carry `source`/`prompt_version`
   so the UI always shows *what* produced them.
3. **SMTP unconfigured** → crisis notifications are logged, never thrown.
4. **Classifier missing** (`emotion_model.pkl`) → `/health` reports `degraded`; emotion
   fields degrade to `neutral`; risk rules still run (`risk_engine.py` is rule-based).

Nothing that runs on AI output can take autonomous clinical action — that is the
`CrisisPolicy` boundary (`app/ml/crisis_policy.py`).

## Manual deploy checklist

1. `git push` → Render Blueprint reads `render.yaml` and builds both Docker services.
2. Set `JWT_SECRET` (auto-generated by Blueprint on first deploy).
3. Verify `GET /health` on the backend service shows `status: healthy` (or `degraded`
   only if no AI provider is reachable).
4. Open the frontend service; the login page must load (nginx on `PORT`).
5. Local first run: `LOG_FORMAT=text` keeps dev logs readable.
