# Sentinel — Free Hosting & Pilot Deployment Plan (2026)

Goal: run the full Sentinel stack (FastAPI backend + React/Vite frontend + AI
classifiers) at **$0/month** for a 50–100 user pilot, with a straightforward
path to paid when real traffic arrives.

> **What's live right now (recommended pilot setup):** your laptop *is* the
> server (FastAPI + SQLite) and a free **Cloudflare Tunnel** exposes it to the
> internet behind HTTPS. No cloud hosting, no domain, no credit card — data
> stays on your machine. See §0.

The stack today:
- Backend: FastAPI + uvicorn, SQLAlchemy, **SQLite** (WAL), JWT auth, device
  tokens, optional LLM backends (Groq / local Ollama).
- Frontend: React 19 + Vite + Tailwind (static build), served by FastAPI
  itself (same-origin) and installable as a **PWA**.
- AI: emotion analysis + triage via `app/ml/emotion_classifier.py` (local
  sklearn model) or an LLM provider.

---

## 0. Laptop as server + Cloudflare Tunnel (the $0 pilot — running now)

This is what the clinic pilot runs on. No cloud infra at all:

```
                      ┌─ Cloudflare edge (TLS) ─┐
  phone / browser ──▶ │  https://<rand>.trycloudflare.com
                      └────────────┬────────────┘
                                   │  (secure tunnel, outbound-only)
                                   ▼
                      ┌─ your laptop ─────────────────┐
                      │  cloudflared  →  :8000        │
                      │  FastAPI serves:              │
                      │    /api/*      → API routes   │
                      │    /           → frontend dist│  (same-origin, PWA)
                      │  SQLite (WAL) in backend/data/│  (all data stays here)
                      └───────────────────────────────┘
```

**Why it's a good fit:**
- $0, no account for quick tunnels, HTTPS automatic, works behind home NAT
  (outbound-only — no port forwarding).
- Data physically stays on your laptop (privacy win for a mental-health pilot).
- PWA installs to the phone home screen; `/api` is same-origin (no CORS).

**Quick tunnel (no domain, URL changes each run):**
```
cloudflared tunnel --url http://127.0.0.1:8000
```
Output includes `https://<random>.trycloudflare.com`.

**Named tunnel (free, permanent `sentinel.yourdomain.com`):**
1. Buy a domain (~$8–10/yr; you have a Cloudflare account already).
2. In Cloudflare dashboard: Zero Trust → Networks → Tunnels → Create →
   route `sentinel.yourdomain.com` → `http://localhost:8000`.
3. Run `cloudflared tunnel run <name>` on the laptop.
4. URL never changes; call it `sentinel.<yourdomain>`.

**Ops notes for the "laptop is the server" model:**
- Keep the laptop wired + awake (or leave the tunnel + uvicorn running).
- Start uvicorn from `backend/`: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
  (the static mount + PWA come along automatically).
- For the clinic, add a free uptime watchdog (UptimeRobot pings `/health`) and
  restart the tunnel on boot (Windows: Task Scheduler).
- Backups: SQLite file + `-wal` are the whole world; snapshot them nightly to
  cloud storage (encrypted).

---

## 1. The three moving parts and where they go

| Part | Best free option | Why |
|------|------------------|-----|
| **Frontend (static)** | **Cloudflare Pages** (or Vercel) with a `/api` rewrite to the backend | Free, global CDN, HTTPS, custom domain, no sleep. Vite build is a `dist/` static bundle. |
| **Backend (FastAPI)** | **Railway** ($5/mo credit, ~500h free, no sleep) OR **Render** (750h/mo free but sleeps) | Always-on for a live pilot is worth the tiny credit. See full comparison in §2. |
| **Database** | **Neon** or **Supabase** (free Postgres) | SQLite is fine solo, but for 50–100 concurrent writes a managed Postgres removes the write-lock tail. Drop-in via `DATABASE_URL`. |
| **LLM / AI** | **Groq free tier** (30k token/min) | Fast Llama/Qwen inference, no credit card. Local sklearn fallback stays. |

### Frontend ↔ backend wiring (read this before deploying)

The frontend is **already same-origin**: `frontend/src/api/client.ts` uses a
relative `BASE = '/api'`, and FastAPI serves the built `dist/` via
`app/main.py:201-215` (a `/assets` mount + SPA fallback). So for the laptop +
tunnel setup, **nothing extra is needed** — browser, `/api`, cookies, and SW
all share one origin.

If you later split the frontend to a CDN (Cloudflare Pages/Vercel), `/api/*`
must be rewritten to the backend origin and CORS + `COOKIE_SECURE=true` set.

### PWA is included

- `frontend/public/manifest.webmanifest` — name, icons (192/512/maskable),
  standalone display, shortcuts (Journal, Emergency). Semi-opted into
  installability.
- `frontend/public/sw.js` — precaches the app shell; network-first for `/api`
  with cached fallback; stale-while-revalidate for static assets.
- `frontend/src/main.tsx:7` registers the SW on load.
- `theme-color` is now dynamic (dark `#151824` / light `#F4F9F8`), so the
  Android status bar matches the active theme.
- Rebuild after editing `public/`: `npm run build` → `dist/` (gitignored).

> Privacy note (important): free LLM tiers may train on your prompts. For a
> live pilot with real patient mental-health data, route AI through the local
> sklearn classifier, or use **paid** Groq/Mistral. Keep patient data out of
> free LLM tiers. See §6.

---

## 2. Backend hosting — honest free-tier comparison (verified 2026)

| Platform | Free tier | Sleeps? | FastAPI? | Card? | Verdict for pilot |
|----------|-----------|---------|----------|-------|-------------------|
| **Railway** | $5/mo credit (~2–3 small apps always-on) | No | Yes (Nixpacks/auto-detect) | Yes | **Best default** — no cold starts, real DBs |
| **Render** | 750 h/mo web service + free Postgres | Yes (after 15 min idle) | Yes | No | Good if traffic is steady; sleeps otherwise |
| **Fly.io** | 3 free shared VMs (256 MB) | No | Yes (Docker) | Yes | Great, but more ops; Docker required |
| **PythonAnywhere** | 1 web app, always-on | No | **No ASGI** (FastAPI won't run) | No | Skip — no ASGI on free tier |

**Recommendation:** **Railway** for the live backend. One web service +
attach their managed Postgres. The `$5` credit typically covers a small
always-on API + Postgres for the pilot length. If you want a strict $0/card
sign-up, **Render** works but the 15-minute spin-down gives 30–60 s cold
starts on first hit — unacceptable for a live dashboard, so you'd pair it
with an UptimeRobot ping.

Why not the others for the *backend*:
- Vercel = serverless, no persistent process / WebSockets (the WS crisis path
  won't work); static frontend only.
- Cloudflare Workers = same serverless limits.

---

## 3. PostgreSQL migration (needed before cloud DB)

SQLite works today and our load-tested it to 100 concurrent writers with no
data loss (see below), but a managed Postgres removes the p99 latency tail and
gives backup/HA. The code is already portable:

- `app/core/database.py` branches only on the `sqlite` substring — pointing
  `DATABASE_URL=postgresql://user:pass@host/db` auto-enables the connection
  pool (`pool_size=10`, `max_overflow=20`).
- No SQLite-specific SQL in queries (only the pragma listener, which is gated
  to sqlite).
- One change needed: `app/core/health.py` uses `PRAGMA user_version` to verify
  writes; Postgres should use a tiny write to a `health_checks` row instead.

Migration steps:
1. `pip install "psycopg[binary]"` (add to requirements.txt).
2. Create the Postgres DB (Neon free auto-provisions a connection string).
3. Run the schema create (the app does `Base.metadata.create_all` at startup;
   for a clean cloud bring-up this is fine for a pilot).
4. Point `DATABASE_URL` at it and run the test suite against Postgres before
   switching the live service.

---

## 4. Reference $0 architecture

**Recommended (same-origin, simplest):** the built frontend is served by the
FastAPI backend, so browser, `/api`, and cookies all share one origin.

```
            ┌─ Railway web service ────────────────────────┐
            │  uvicorn app.main :PORT                      │  ENV:
 browser ──▶│  serves /            → frontend dist/        │  DATABASE_URL=postgres://…
            │  serves /api/*       → FastAPI routes        │  JWT_SECRET=<strong>
            │  sets cookies (path="/")                     │  ENCRYPTION_REQUIRED=true
            └──────────────┬───────────────────────────────┘  RATE_LIMIT_MAX=300
                           │
                  ┌─ Neon / Supabase ─┐
                  │ Postgres (0.5–5 GB)│
                  └────────────────────┘

AI: app falls back to local sklearn classifier; optionally Groq free tier for
    LLM triage summaries (keep patient data local unless paid).
```

**Optional CDN split (option 2):** put `dist/` on Cloudflare Pages with a
`/api/*` rewrite to the backend, then set `CORS_ORIGINS` to the frontend origin
and `COOKIE_SECURE=true`.

- CORS: already configurable via `CORS_ORIGINS` env (defaults
  `http://localhost:5173`; set to your frontend origin, or leave default for
  same-origin hosting).
- HTTPS everywhere: Railway + Neon give TLS automatically.
- `cookie_secure=true` once HTTPS is live.

---

## 5. One-click-ish deploy checklist (Railway + Cloudflare + Neon)

Backend (Railway):
1. `git init` the repo (already a git repo) and push to GitHub.
2. Railway → New Project → Deploy from GitHub → choose the `backend/` as the
   root, add `railway.json`:
   ```json
   {
     "build": { "builder": "NIXPACKS" },
     "deploy": { "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT" }
   }
   ```
3. Add env vars: `DATABASE_URL`, `JWT_SECRET` (strong random),
   `ENCRYPTION_REQUIRED=true`, `CORS_ORIGINS`, `RATE_LIMIT_MAX=300`.
4. Add Railway Postgres (or external Neon URL) and attach.

Frontend (Cloudflare Pages — only for option 2 above):
1. `npm run build` → `dist/` output (the Vite default outDir — already
   `.gitignore`d).
2. Cloudflare Pages → Upload / GitHub → root `frontend/`, build command
   `npm install && npm run build`, output directory `dist`.
3. Add a `/api/* → backend` rewrite/pages-rule and set `CORS_ORIGINS` on the
   backend (or use the simpler same-origin option 1 and skip CDN entirely).

> For the pilot, prefer **option 1 (same-origin)** — the frontend served by
> FastAPI — unless you specifically want the CDN. Same-origin needs no CORS
> config and no rewrite rules.

Keep-alive (only if you pick Render's sleeping tier):
- UptimeRobot pings `/health` every 5 min.

---

## 6. Security / privacy guardrails for free hosting

- **Patient data + free LLM = no.** Keep AI classification on the local
  sklearn model for the pilot, or pay for Groq. Free tiers may train on data.
- **Secrets:** use the platform's env-var panel; never commit `.env`. Confirmed
  `.env`, `data/`, `*.db*`, and `frontend/dist/` are already `.gitignore`d.
- **`ENCRYPTION_REQUIRED=true`** in cloud — this app's encryption writes
  (`raw_json`, journal fields via `EncryptedText`) need the master key.
  Provide `SENTINEL_ENCRYPTION_PASSPHRASE`/salt via env and call
  `/api/auth/unlock` (or set `ENCRYPTION_REQUIRED=true` with passphrase) so
  launches fail closed rather than write plaintext.
- **TLS + secure cookies**: set `COOKIE_SECURE=true`.
- **Update the rate limiter**: default now 300/min, and authenticated
  `/ring/data` device pushes bypass the per-IP limiter (they use device
  tokens, not IP). Keep the per-IP cap on login/register.
- **Real JWT secret**: the app refuses the default `change-me-…` secret at
  startup when `debug=false`.

---

## 7. What we verified locally (this session) — so you can ship it

- **Idempotency**: `/ring/data` dedupes by `(device_id, seq)`; under a 100-user
  load dump with retries + offline-buffer bursts, **0 duplicate rows** ever
  landed (2907 rows / 2907 distinct seq).
- **100-user pilot load, no hardware** (software ring clients):
  - Fast cadence (~4 s/device): **100% success**, 0 network errors, 0 dups.
    p99 `/ring/data` ≈ 1.8 s (SQLite write-lock tail).
  - Realistic cadence (~15 s/device): **100% success**, 0 dups. p99 ≈ 2.2 s.
- **50-user pilot load** (realistic 15 s cadence + offline burst): **100%
  success**, 0 dups, p99 ≈ 1.1 s — confirms the lower bound of the pilot range.
- **Rate limiter fix**: raised default to 300/min (configurable), and
  authenticated device pushes are exempt from the per-IP limiter — otherwise a
  shared NAT IP throttles all 100 devices (we hit exactly this in testing).
- **SQLite handled 100 concurrent writers** with WAL and zero data loss; the
  2 s p99 tail is why we recommend moving to managed Postgres for production.
- **Live public URL verified**: the running Cloudflare Tunnel serves the SPA,
  `/api`, hashed assets, `manifest.webmanifest`, `sw.js`, and deep SPA routes
  (e.g. `/journal`) with working React fallback — all through the tunnel.

Bottom line: **the pilot is live at $0 on your laptop behind a Cloudflare
Tunnel** (URL in §0). If you later want always-on without your laptop, the same
app deploys to Railway + Neon/Supabase + Cloudflare Pages unchanged. SQLite
carries 100 concurrent writers today; plan the Postgres swap before real users.

## 8. Cost floor when you graduate past free

- **Cloudflare Tunnel + laptop: $0 forever** until you need HA/uptime.
- Railway pay-as-you-go: ~$5–15/mo for this workload.
- Render Starter: $7/mo (no sleep).
- Neon/Supabase Pro: ~$25/mo (or keep free with a keep-alive ping).
- Domain for the named tunnel: ~$8–10/yr.
- Groq paid: pennies for the triage volume.
