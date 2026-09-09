# Sentinel — Deployment Guide

Sentinel deploys to Render via a Docker Blueprint (`render.yaml`). This document is the
operating contract: how it is built, what every environment variable does, and what
degrades gracefully when pieces fail.

## Services

| Service | Render type | Runtime | Docker context | Health check |
|---------|-------------|---------|----------------|--------------|
| `sentinel-backend` | web | docker | `./backend` | `GET /health` |
| `sentinel-frontend` | web | docker | `./frontend` | `GET /` |
| `sentinel-scheduler` | worker | docker | `./backend` | — (runs `python -m app.workers.runner`) |

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
| `GROQ_API_KEY` | unset | cloud fallback provider; only used if `ALLOW_CLOUD_AI=true` |
| `ALLOW_CLOUD_AI` | `false` | **default-off**; if `true`, raw journal text may be sent to Groq (third-party LLM) when Ollama is unavailable. Privacy-first clinics must keep it off |
| `SENTINEL_BACKUP_KEY` | unset | Fernet key for `scripts/backup_db.py`; if unset a machine-local key is derived (not portable). Keep separate from the backups |
| `SENTINEL_TRUSTEE_LINK_SECRET` | unset | HMAC key for signed trustee-portal links; falls back to `JWT_SECRET` |
| `SENTINEL_TRUSTEE_LINK_EXPIRE_SECONDS` | `3600` | lifetime of a signed trustee alert link |
| `SMTP_HOST/PORT/USER/PASSWORD` | gmail defaults | for crisis notifications; unset → email disabled (logs only) |
| `EMAIL_FROM`, `CRISIS_HELPLINE_EMAIL` | — | sender + helpline contact (crisis escalation) |
| `LOG_FORMAT` | `json` | `json` = one JSON object per line; `text` = human-readable |
| `RATE_LIMIT_BACKEND` | `memory` | `memory` = in-process sliding window (single worker); `db` = fixed-window counters shared via `DATABASE_URL` |
| `WS_PUBSUB` | `auto` | `auto` = PG `LISTEN/NOTIFY` when `DATABASE_URL` is postgres; `pg` = force; `off` = single-process local broadcasts |
| `SCHEDULER_LOCK_KEY` / `SCHEDULER_HEARTBEAT_SECONDS` | `749493` / `10` | advisory-lock leader election; the key must match across scheduler replicas |
| `RUN_WORKERS` | `true` | `false` on API processes when a dedicated scheduler service runs the loops |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | `10` / `20` | SQLAlchemy pool for PostgreSQL/MySQL (ignored for SQLite) |
| `DB_POOL_TIMEOUT` / `DB_POOL_RECYCLE` / `DB_POOL_PRE_PING` | `30` / `1800` / `true` | pool health defaults |

All settings are read in `backend/app/core/config.py` (`pydantic-settings`, env file
`../.env` for local dev).

## Running at scale

Sentinel is multi-worker safe by design:

- **Single active scheduler with failover.** Reminder + celebration loops use a PG
  advisory lock (`pg_try_advisory_lock` on `SCHEDULER_LOCK_KEY`). Any number of
  scheduler replicas can run; exactly one holds the lock and sweeps, and the lock
  is freed automatically if that process dies, so a replica takes over. API workers
  set `RUN_WORKERS=false`; the `sentinel-scheduler` service (or Docker
  `--profile scaled` service) runs `python -m app.workers.runner`.
- **Cross-worker WebSocket fan-out.** Crisis/discrepancy broadcasts use PostgreSQL
  `LISTEN/NOTIFY` (`WS_PUBSUB=auto`): every API worker publishes alerts to the
  `sentinel_ws` channel, every worker listens on a dedicated connection and pushes
  to its own local dashboard clients — so a client connected to ANY worker sees
  the alert. On SQLite this stays single-process/local automatically.
- **Shared rate limits.** `RATE_LIMIT_BACKEND=db` moves the per-IP budget from per-process
  memory into `rate_limit_counters` (atomic upsert), so the budget holds across N workers.
- **Shared revocation.** The JWT blacklist is DB-backed (`token_blacklist` table), so a
  logout on one worker is honored by all.
- **PostgreSQL.** `DATABASE_URL=postgresql://...` gives real multi-writer concurrency and
  pooling (`psycopg2-binary` is in `requirements.txt`). Schema is managed by Alembic
  (`alembic upgrade head`; migration `9f3e2a1b7c4d` adds the two scale tables).
  `alembic/env.py` honors `DATABASE_URL` and bootstraps a fresh database from the ORM
  before applying idempotent migrations, so empty DBs and already-formed DBs both
  converge to head. SQLite remains the default for local dev.
- **Crisis state and syncs are always DB-persisted**; the pub/sub layer only pushes
  dashboards, so nothing is lost if a publish fails.

Local scaled layout:

```bash
docker compose --profile scaled up -d   # postgres + backend (4 workers) + scheduler
```

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

**Off-box encrypted backups:** run `python -m scripts.backup_db` from `backend/`. It makes
a consistent SQLite snapshot, encrypts it with Fernet, writes it to a durable local dir,
and — if `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` are set —
uploads the ciphertext to S3-compatible object storage (never plaintext PHI). Local copies
are pruned to the last `--keep` (default 7). For recoverable backups set `SENTINEL_BACKUP_KEY`
explicitly and keep it separate from the backup files.

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
