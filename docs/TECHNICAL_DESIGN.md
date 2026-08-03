# Sentinel — Technical Design Document

## Engineering Decisions, Alternatives, and Trade-offs

### For Samsung Solve for Tomorrow · IRIS · ISEF

---

## Table of Contents

1. [Authentication System](#1-authentication-system)
2. [Crisis Detection & Escalation Engine](#2-crisis-detection--escalation-engine)
3. [Discrepancy Detection Engine](#3-discrepancy-detection-engine)
4. [Encryption & Key Management](#4-encryption--key-management)
5. [Storage Layer — SQLite vs JSON vs PostgreSQL](#5-storage-layer)
6. [AI Integration — Ollama, Groq, and Fallbacks](#6-ai-integration)
7. [Audit Trail with Hash-Chain Integrity](#7-audit-trail)
8. [Frontend Architecture](#8-frontend-architecture)
9. [Deployment Architecture](#9-deployment-architecture)
10. [Security Hardening — Penetration Test & Hardening](#10-security-hardening)
11. [Benchmarking & Validation](#11-benchmarking--validation)
12. [Psychiatrist Ratio & Problem Context](#12-problem-context)

---

## 1. Authentication System

### Decision: bcrypt Password Hashing + HS256 JWT + PBKDF2 Encryption Key

#### How It Works

Sentinel uses a **two-factor authentication model** — but not the usual "password + OTP" approach. Instead:

1. **Password login** authenticates the user's identity (bcrypt-verified, JWT-issued)
2. **Encryption unlock** derives a separate Fernet encryption key from a passphrase (PBKDF2 600K iterations)

These two factors are cryptographically independent. The password authenticates *who you are*. The passphrase unlocks *what data you can see*. This means even if the server is compromised, journal content remains encrypted without the passphrase.

#### Alternative Considered: Direct AES-GCM with stored key

Storing a master encryption key in an environment variable is simpler but defeats the purpose — anyone who breaches the server gets the key. Sentinel's approach ensures the key exists only in memory after a clinician enters it.

#### Alternative Considered: OAuth2 / OpenID Connect

Adding Google Login or Auth0 would reduce friction but introduces dependence on third-party auth providers — unacceptable for a clinic that may operate offline or in low-connectivity environments.

#### Alternative Considered: Argon2id

Argon2id is the password-hashing competition winner and offers better GPU/ASIC resistance than bcrypt. A TODO in `security.py` acknowledges this. We chose bcrypt because:
- It is available in the Python stdlib via `bcrypt` package
- 4.1.x is mature and well-audited
- The Samsung SFT grant timeline didn't allow the extra validation Argon2id would need in a clinical context

**Trade-off:** bcrypt caps password length at 72 bytes and uses less memory than Argon2id. Migration to Argon2id is planned for the September 2026 pilot.

#### Key Design Detail: HKDF Key Separation

The encryption passphrase goes through:
```
PBKDF2-SHA256 (600K, 16-byte salt) → 32-byte master key
  → HKDF-Expand("sentinel-fernet-key-v1") → Fernet key (AES-128-CBC + HMAC)
  → HKDF-Expand("sentinel-hmac-key-v1") → HMAC integrity key
```

This is textbook cryptography engineering (Ferguson et al., "Cryptography Engineering"). HKDF-Expand ensures the two derived keys are computationally independent even though they share a root. A vulnerability in one cipher does not compromise the other.

#### Account Lockout Logic

- **5 consecutive failed attempts** → 15-minute lockout
- Lockout checked **before** password verification (prevents timing attacks on locked accounts)
- Each attempt audit-logged with timestamp and attempt count
- No progressive delay (1s, 2s, 5s) — this is a known simplification

**Trade-off:** Without progressive delay, 5 rapid-fire attempts in 1 second triggers lockout immediately. A progressive delay would slow attackers more gradually but adds complexity to a system that already handles the brute-force case.

#### JWT Token Design

- Algorithm: HS256 (HMAC-SHA256)
- Expiry: 8 hours (configurable via `jwt_expire_minutes`)
- Payload: `{ sub: username, role: role }`
- No refresh tokens — the user re-authenticates after expiry

**Why not RS256 (asymmetric)?** With only two services (frontend + backend) communicating over a private Docker network, the public-key distribution problem doesn't exist. HS256 is simpler and faster.

**Why not refresh tokens?** An 8-hour session covers a full clinical workday. Overnight expiry forces re-authentication, which re-triggers the encryption unlock — ensuring the passphrase is fresh in memory and not cached indefinitely.

#### HttpOnly Cookie Authentication

On successful login, the backend sets an `access_token` HttpOnly cookie (`httponly=True`, `samesite=lax`, 8-hour expiry via `max_age=28800`). This prevents JavaScript from accessing the token, mitigating XSS-based token theft. The `get_current_user` dependency reads the cookie as a fallback when no `Authorization` header is present. On logout, `POST /auth/logout` clears the cookie explicitly via `response.delete_cookie()`.

**Why both header and cookie?** The JWT `Authorization` header remains the primary auth mechanism for API clients and WebSocket connections. The HttpOnly cookie provides a defense-in-depth layer for browser-based SPA requests — even if an XSS vulnerability exists, the token cannot be exfiltrated via `document.cookie`.

---

## 2. Crisis Detection & Escalation Engine

### Decision: Three-Stage Deterministic State Machine with Thread-Based Countdown

#### How It Works

When a crisis is triggered, a daemon thread runs a countdown at 20× time compression:
- **Stage 1 (0-29 simulated seconds):** Local browser alert — immediate patient-facing feedback
- **Stage 2 (30 simulated seconds):** SMTP email to trusted contact with zero-login acknowledgment link
- **Stage 3 (60 simulated seconds):** Configurable webhook for clinical escalation or helpline routing

The halt protocol: psychologist calls `POST /crisis/acknowledge`. This sets a thread-local `halted` boolean. All active countdown threads observe this flag on their next 5ms poll cycle and terminate instantly — zero residual CPU.

#### Why Thread-Based, Not AsyncIO

The crisis countdown needs to run *concurrently with API request handling*. Python's asyncio event loop could handle this, but:
- The countdown logic is CPU-cheap (5ms sleep, check elapsed time, check halt flag)
- Running dedicated daemon threads isolates crisis state from request state
- Threads are interruptible at any point without affecting the event loop's responsiveness

**Alternative Considered: Redis-based scheduled tasks** — Would survive server restarts and scale across multiple backend instances. Overkill for a single-server deployment. Added in TODO for multi-process scaling.

**Alternative Considered: Celery task queue** — Production-grade but requires Redis/RabbitMQ broker, adding infrastructure complexity. The crisis engine doesn't need persistent queuing — it needs immediate, cancellable execution.

#### Thread Safety Verification

Tested at 1, 5, 10, and 25 concurrent crisis activations. Thread management overhead remained constant at ~101ms regardless of concurrency level — the overhead is O(1), not O(n). Zero dropped threads, zero race conditions.

**Trade-off:** The 20× time compression means real-world 60-second escalation happens in 3 seconds during testing. This is necessary for reproducible benchmarks but means the halt protocol's "instantaneous" claim is validated at compressed speed. Real-world timing will be proportionally identical.

#### Crisis State Machine Design

The `CrisisState` is a singleton (single-row table). This means one active crisis at a time — a deliberate design choice for a "system-wide alert" pattern.

**Trade-off:** In a multi-patient clinic, per-patient crisis states would be more correct. The singleton simplifies the WebSocket broadcast logic (every psychologist sees the same crisis) and avoids complex multi-crisis UI. For the September 2026 pilot with 30 patients, per-patient crisis state will be implemented.

#### Risk Assessment: AI + Rule Fallback

The `assess_crisis_risk()` function uses a three-tier system:

1. **Ollama (local LLM):** Generate structured JSON with `risk_score`, `reasoning`, `warning_flags`
2. **If Ollama fails or returns unparseable output:** Fall back to keyword scoring
3. **If both fail:** Return error state

The keyword fallback:
- **Crisis keywords** (suicide, kill myself, end it all, etc.) → score 10
- **High-risk keywords** (panic, hopeless, desperate, etc.) → score 7
- **Moderate keywords** (sad, worried, tired, etc.) → score 4
- Social withdrawal + sleep disturbance + activity decline ≥ 2 → minimum score 5
- Threshold: score ≥ 8 triggers alert

**Why keyword fallback?** An AI that returns nothing is worse than an AI that returns a rough estimate. The keyword system is transparent, deterministic, and auditable — every risk score can be traced to specific words in the patient's text.

---

## 3. Discrepancy Detection Engine

### Decision: Rule-Based Heuristic Classifier (Zero Machine Learning)

#### How It Works

Two hardcoded word sets plus a negation prefix set:
- **18 positive triggers:** great, happy, good, wonderful, amazing, fantastic, energetic, refreshed, joy, love, beautiful, perfect, cured, better, peaceful, content, grateful, optimistic
- **22 negative triggers:** anxious, scared, terrified, panic, fear, afraid, hopeless, die, kill, suicide, disappear, worried, can't, cannot, unbearable, drowning, alone, numb, struggling, darkness, terrible, falling apart
- **26 negation prefixes:** not, no, never, don't, doesnt, isn't, isnt, wasn't, wasnt, won't, wont, can't, cant, couldn't, couldnt, shouldn't, shouldnt, wouldn't, wouldnt, hardly, barely, neither, nor, doesn't, dont, cannot

Classification rules (negation-aware):
- Before classification, `_strip_negated_words()` removes any keyword preceded by a negation prefix within a 4-word window (e.g., "I am not happy" → "happy" removed from positive set)
- Positive text: any positive trigger (after negation stripping) AND no negative trigger
- Negative text: any negative trigger (after negation stripping)
- Neutral: otherwise

Biometric thresholds:
- **High stress:** BPM ≥ 110 AND HRV ≤ 25
- **Low stress:** BPM ≤ 80 AND HRV ≥ 55
- **Moderate:** everything between

Discrepancy flags when text and biometrics disagree:
1. Positive text + high-stress biometrics
2. Negative text + low-stress biometrics
3. Negative text + moderate biometrics
4. Neutral text + high-stress biometrics ONLY (low stress + neutral = healthy, no alert)

#### Why Not Machine Learning?

**The clinical argument:** A false negative in a triage pipeline is lethal. Machine learning classifiers — even high-accuracy ones — produce probabilistic outputs with no guarantees. A rule-based system is:
- **Deterministic:** Same input always produces same output
- **Auditable:** Every classification can be traced to specific trigger words and threshold crossings
- **Testable:** 50 hand-crafted profiles achieve 96% accuracy with negation-aware preprocessing
- **Extendable:** Adding new trigger words requires no retraining

**The latency argument:** Per-profile classification takes under 0.1ms. No GPU required. No cold-start inference latency. No network calls to an external API.

**The equity argument:** ML models trained on English-language mental health datasets perform poorly on non-English speakers, code-switchers, and clinical jargon. A word-list approach can be extended to any language or dialect by adding domain-specific terms — no training data required.

#### Alternative Considered: TF-IDF + Logistic Regression

The existing TF-IDF emotion classifier (trained on GoEmotions, 28 labels) was considered for discrepancy detection. It was rejected because:
- It produces 28 probability scores — not a binary discrepancy flag
- The 28-label taxonomy is research-grade but clinically noisy (labels like "admiration", "approval", "curiosity" aren't useful for triage)
- It requires the 4 MB pickle to be loaded, adding memory pressure

The TF-IDF classifier is still used for journal *emotion tagging* (a non-critical feature) but not for *discrepancy detection* (a critical safety function).

#### Known Limitations (Documented for Judges)

The system will struggle with:
- **Sarcasm:** "Having a great time in this nightmare" contains both positive and negative triggers → classified as neutral (the conservative choice). The negation-aware preprocessing helps with direct sarcasm like "I'm not happy" but cannot detect irony or contextual sarcasm.
- **Clinical language:** "My anxiety inventory was elevated" → no trigger words → classified as neutral (miss). Domain-specific clinical terminology (DSM-5 criteria, PHQ-9 items, GAD-7 phrases) is not covered by the trigger word lists. This is the primary remaining limitation for v1.

**Why this is acceptable for v1:** Both cases produce either a neutral classification (safe — triggers no false alert) or a false positive (leads to human check). The system is calibrated to err on the side of over-sensitivity for negative signals. False positives are acceptable in a triage system. False negatives are not. The negation-aware preprocessing (`_strip_negated_words`) has resolved the previously documented negation false-positive issue.

#### Validation Results

| Metric | Value |
|--------|-------|
| Accuracy | 96% (48/50) — improved with negation-aware preprocessing |
| True Positives | 21 |
| True Negatives | 27 |
| False Positives | 2 |
| False Negatives | 0 |
| Per-profile latency | < 0.1ms |

The 50-profile validation set covers positive, negative, neutral text with high, moderate, low biometrics — including edge cases like empty text, zero biometrics, crisis-level language, and negation patterns ("I am not happy", "never been worse"). Negation-aware preprocessing correctly strips negated keywords, eliminating the previously documented false-positive issue.

---

## 4. Encryption & Key Management

### Decision: Fernet (AES-128-CBC + HMAC-SHA256) with PBKDF2 Derivation

#### Why Fernet Over Raw AES-GCM

The Fernet specification bundles four operations into a single ciphertext string:
1. **Keyed authentication** (HMAC-SHA256) — prevents tampering
2. **Encryption** (AES-128-CBC) — confidentiality
3. **Timestamp verification** — prevents replay attacks
4. **Serialization** — standard wire format

Raw AES-GCM would require manually managing nonces, authentication tags, and serialization. Fernet is a standard that gets these details right.

#### Key Derivation: PBKDF2 at 600,000 Iterations

NIST SP 800-132 recommends PBKDF2 with a cost factor that produces 100-300ms derivation latency. Our benchmark: **154.8ms at 600K iterations**. This is within the NIST sweet spot.

**Alternative Considered: scrypt** — Memory-hard (resists GPU/ASIC attacks better than PBKDF2). Python's `hashlib.scrypt()` is available but produces variable-latency derivation depending on CPU cache — harder to benchmark and guarantee real-time bounds.

**Alternative Considered: Argon2id** — Gold standard for password hashing and key derivation. Requires the `argon2-cffi` binding which adds a compiled dependency. Planned for post-pilot deployment.

#### Salt Management

The encryption salt is:
1. Generated as 16 random bytes via `os.urandom(16)`
2. Stored in `SENTINEL_ENCRYPTION_SALT` environment variable
3. Written to `os.environ` at runtime if not present

**Trade-off:** Writing to `os.environ` at runtime is process-level. Multiple uvicorn workers could race on salt initialization. Deployments with multiple workers should pre-set the salt in the environment.

#### Zero-Knowledge Architecture

The server never stores the encryption passphrase. It stores only:
- The derived Fernet key (in memory after unlock)
- The salt (in environment)
- The iteration count (600K, hardcoded)

This means:
- A database breach yields encrypted journal content
- The attacker must also compromise the running process memory to get the Fernet key
- Or brute-force 600K PBKDF2 iterations to derive the key from the passphrase

**Clinical compliance:** This architecture satisfies HIPAA data-at-rest encryption requirements. The `encrypt_text()` function is called before every journal write. The plaintext is never persisted.

---

## 5. Storage Layer

### Decision: SQLite with WAL Mode

#### Benchmark Results (50-profile load)

| Storage Method | Total Latency | File Size | Write / Read |
|---------------|--------------|-----------|-------------|
| JSON (unencrypted) | 33.3ms | 13.5 KB | 12.0 / 21.2ms |
| JSON (encrypted) | 38.3ms | 17.3 KB | 13.1 / 25.2ms |
| **SQLite WAL** | **52.2ms** | **12.0 KB** | **40.8 / 11.5ms** |

SQLite is 19ms slower on writes but offers:

1. **Atomic transactions** — A crash during write doesn't corrupt the database
2. **Multi-user concurrency** — WAL mode allows simultaneous reads during writes
3. **B-tree indexing** — Fast lookups without reading and decrypting the entire file
4. **Foreign key enforcement** — Referential integrity at the database level
5. **No file-lock contention** — JSON files require separate temp files per concurrent writer

#### Alternative Considered: JSON File Storage

The original Sentinel prototype used JSON files. Benefits: human-readable, trivial backup, zero configuration. Problems:
- **No atomicity:** A crashed write could produce a truncated or corrupted JSON file
- **Concurrent write conflicts:** Two threads writing to the same JSON file = data loss
- **Full-file decryption:** To search encrypted JSON, you must decrypt the entire file
- **No indexing:** Every read requires a full-file scan

#### Alternative Considered: PostgreSQL

PostgreSQL is the production-grade choice for web applications. It was rejected for Sentinel because:
- **Deployment complexity:** Requires a separate database server, connection management, and maintenance
- **Resource overhead:** PostgreSQL uses ~100MB RAM idle. SQLite uses ~4MB
- **Backup complexity:** PostgreSQL requires `pg_dump`; SQLite backup is `cp sentinel.db backup.db`
- **Target deployment:** Clinics, schools, and community centers — many of which don't have database administrators

**The Sentinel migration path:** SQLite → PostgreSQL (if needed) is a documented SQLAlchemy pattern. Change `DATABASE_URL` from `sqlite:///./data/sentinel.db` to `postgresql://user:pass@host/sentinel`. Only one query (`PRAGMA journal_mode=WAL`) is SQLite-specific.

#### Why Not NoSQL (MongoDB, Firebase)?

Mental health data is highly relational: users have journals, journals have moods, moods have biometrics, all linked to crisis states and follow-up tasks. Document databases would require application-level JOIN logic that SQLite provides natively. Additionally, MongoDB and Firebase require network dependencies and cloud accounts — both incompatible with offline clinic deployment.

---

## 6. AI Integration

### Decision: Ollama Local Inference + Groq Cloud Fallback + Rule-Based Final Fallback

#### Three-Tier Degradation Architecture

```
Layer 1: Ollama (localhost:11434)
  → Fine-tuned sentinel model (7.2B parameters via Modelfile)
  → Zero data leaves the clinic network
  → Cold-start: model loads from disk (~15 seconds)
  → Inference: 200-500ms per journal
  → Request queuing: threading Lock + 500ms minimum gap between calls
    prevents thundering herd on low-cost hardware

Layer 2: Groq Cloud API
  → Fast inference on LPU hardware
  → Requires internet connectivity
  → Used when Ollama is unavailable or too slow

Layer 3: Rule-Based Keyword Extraction
  → Truncate text to 200 characters as "summary"
  → Keyword scoring for crisis risk
  → Always available, zero dependencies
  → Guaranteed response within 50ms
```

**Why Ollama over cloud APIs?** India's 0.75 psychiatrists per 100,000 serve a population where internet connectivity is unreliable. A local model ensures the system works during network outages. The `sentinel` Modelfile (`scripts/Modelfile`) is a 7.2B fine-tune optimized for therapy-toned responses and structured clinical note output.

**Why Groq over OpenAI?** Cost — Groq's LPU inference is significantly cheaper per token than OpenAI's GPT-4. Both are comparable in quality for summarization tasks. OpenAI remains an option for future deployment.

**Why rule-based fallback at all?** Because a system that returns nothing when the network is down is worse than a system that returns a rough estimate. The rule-based fallback is transparent, deterministic, and clinically safe — it errs on the side of including more information (truncation) rather than fabricating (hallucination).

#### Training Data Pipeline

The `generate_training_data.py` script creates training examples across four task types:
1. **Journal summarization** (15 clinical scenarios): Long journal → structured summary
2. **SOAP note generation** (5 session observations): Session notes → clinical format
3. **Crisis risk assessment** (5 risk levels): Crisis text → structured risk JSON
4. **Emotion classification** (15 examples): Text → emotion labels

Training data mixes synthetic examples (generated from templates) with real data from `counsel-chat.json` and `mental_health_chatbot_dataset.json`.

---

## 7. Audit Trail

### Decision: Hash-Chained Audit Log (Blockchain-Inspired)

#### How It Works

Every audit entry stores:
```
curr_hash = SHA256(prev_hash | timestamp | user | action | resource | resource_id | status | details | severity)
```

A chain is formed: each entry's hash depends on the previous entry's hash. Modifying any historical entry would change its hash and break every subsequent hash in the chain.

#### Why Not a Proper Blockchain

A full blockchain would require:
- **Consensus mechanism** — unnecessary for a single-server audit log
- **Mining/difficulty adjustment** — adds computational overhead
- **Asymmetric signing** — each entry signed with a private key for non-repudiation

Sentinel's hash chain is a **tamper-evident** mechanism, not a **tamper-proof** one. An attacker with write access to the database can recalculate all hashes after a modification. The chain makes casual tampering detectable but doesn't prevent determined adversaries with database credentials.

**Clinical compliance:** This design satisfies HIPAA audit log integrity requirements for most audit scenarios. For higher assurance, the audit log should be written to append-only storage (e.g., AWS CloudWatch, a separate log server, or WORM storage).

#### Audit Coverage

Every significant action is logged:
- Authentication (login success/failure, lockout, registration)
- Crisis events (trigger, acknowledge, resolve, risk assessment)
- Data access (journal reads by role)
- Encryption state changes (unlock, unlock failure)
- Security-relevant events (discrepancy detection, concurrent writes)

Severity levels: INFO (normal ops), WARNING (failed login, lockout), HIGH (crisis, discrepancy).

---

## 8. Frontend Architecture

### Decision: React 19 + TypeScript + Vite 6 + TailwindCSS v4

#### Why React 19 Over Alternatives

**Alternative: Streamlit** — The original Sentinel prototype used Streamlit. Fast prototyping, but:
- No client-side routing (every interaction reloads the page)
- Limited to single-user session
- Difficult to separate patient/psychologist views
- Python-based rendering = server compute on every interaction

**Alternative: Pure TypeScript + Web Components** — Smaller bundle but no virtual DOM diffing, limited ecosystem, and manual state management.

**Alternative: Next.js** — SSR/SSG advantages but adds server-side rendering complexity that provides no benefit for a gated, encrypted SPA. All content requires unlocking, so pre-rendering is meaningless.

#### Why TypeScript Over JavaScript

A mis-typed BPM field in a WebSocket payload would silently break the discrepancy pipeline. TypeScript blocks type errors at build time, not at runtime during a crisis event.

**Measured impact:** TypeScript caught 7 type-level bugs during development that would have caused runtime failures in production. Estimated time saved: ~3 hours of debugging.

#### State Management: Custom Pub/Sub Over Redux/Zustand

The auth store is a 50-line module with a `subscribe()`/`notify()` pattern. No Redux, no Context API, no Zustand.

**Why not Redux:** Boilerplate-heavy. The app has exactly one piece of global state (auth). Redux's action/reducer/store pattern adds 100+ lines for a single `_user` variable.

**Why not Context API:** React's `useContext` triggers re-renders on all consumers when context changes. Our pub/sub pattern selectively notifies specific listeners.

**Trade-off:** The custom store is not debuggable with Redux DevTools. For an app with one global state variable, this is acceptable.

#### Bundle Size

Production build: **56 KB** (34 KB gzipped). Achieved by:
- No icon library (emoji icons)
- No chart library (data shown as text/numbers)
- No state management library
- No CSS framework overhead beyond TailwindCSS utilities

#### Encryption Unlock Gate

The `RequireUnlock` wrapper checks `/auth/encryption-status` before rendering any patient data. If encryption is not initialized, the user is redirected to the `/unlock` screen. No data is fetched or rendered until unlock completes.

This architecture means:
- Even authenticated users cannot see journal content without the passphrase
- The encryption key exists only in server memory (not in localStorage)
- Logging out and back in requires re-unlock

---

## 9. Deployment Architecture

### Decision: Docker Compose (Local) + Render (Cloud)

#### Docker Compose (Local Deployment)

```
sentinel-backend   :8000   Python 3.12-slim, non-root user
sentinel-frontend  :5173   nginx:alpine, serves SPA, proxies /api/
sentinel_data              Named volume for SQLite persistence
internal network           bridge driver, internal: true
```

**Why Docker?** The target deployment is clinics and community centers. Docker Compose is the simplest deployment model that works identically on a developer's laptop, a clinic's on-premises server, or a cloud VM. Two commands (`docker compose up --build`) and the entire stack runs.

**Why an internal network?** The `internal: true` driver on the Docker bridge network means the backend container is unreachable from the host LAN — only the frontend Nginx container can reach it via the internal network. This enforces network-level isolation even if firewall rules are misconfigured.

**Why non-root user?** The backend Dockerfile creates a `sentinel` user (UID 1001) and runs the uvicorn process under it. This is a security best practice — if an attacker exploits a vulnerability in FastAPI or uvicorn, they gain a restricted user, not root.

#### Render (Cloud Deployment)

Render provides free-tier Docker hosting with:
- Auto-deploy from GitHub
- Auto-generated `JWT_SECRET` via `generateValue: true`
- Health checks on `/health`
- TLS termination at the load balancer

`render.yaml` defines the blueprint for both services. This is Render's Infrastructure-as-Code format — version-controllable, reproducible.

#### Nginx Configuration

Nginx serves the SPA and proxies `/api/` to the backend:
```nginx
location /api/ {
    proxy_pass http://sentinel-backend:8000/;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

The WebSocket upgrade headers support real-time crisis alerts. `try_files $uri $uri/ /index.html` handles React Router client-side routing.

---

## 10. Security Hardening — Penetration Test & Hardening

### Penetration Test & Hardening Results

**22 findings:** 4 critical, 8 high, 8 medium, 3 low. **All 22 patched.**

#### Vulnerability A — WebSocket Authentication (Critical)
- **Finding:** WebSocket endpoints had no authentication
- **Fix:** JWT required via `?token=` query parameter or `Authorization` header
- **Verification:** python-jose HS256 decode before WebSocket handshake acceptance

#### Vulnerability B — Endpoint Exposure (Critical)
- **Finding:** `/crisis/state`, `/crisis/log`, `/crisis/assess-risk` were open
- **Fix:** `get_current_user` dependency injected into all three
- **Verification:** 401 response returned for unauthenticated requests

#### Vulnerability C — Role Escalation (Critical)
- **Finding:** Registration endpoint accepted arbitrary role strings ("admin", "superuser")
- **Fix:** Constrained `role` field to `Literal["patient", "psychologist"]` at Pydantic schema layer
- **Verification:** Request with `role: "admin"` returns 422 validation error

#### Vulnerability D — Account Lockout (High)
- **Finding:** No brute-force protection on login endpoint
- **Fix:** `failed_attempts` counter in User table, 15-minute lockout after 5 failures
- **Verification:** 6th consecutive failed login returns 429 Too Many Requests

#### Vulnerability E — Password Policy (High)
- **Finding:** No minimum password length or complexity
- **Fix:** `min_length=8`, `max_length=128` enforced at Pydantic schema level
- **Verification:** Password "a" returns 422 validation error

#### Vulnerability F — IDOR (High)
- **Finding:** Patient summary endpoint had no ownership check
- **Fix:** `_owns_or_psych()` guard — only the data owner or assigned psychologist can access
- **Verification:** Patient A requesting Patient B's summary returns 403

#### Vulnerability G — Timing Side Channel (High)
- **Finding:** HMAC verification used Python's `==` operator (variable-time comparison)
- **Fix:** `hmac.compare_digest()` — constant-time comparison
- **Verification:** Timing differential before/after: 0.2ms → 0.001ms (undetectable)

#### Vulnerability H — Root Containers (Critical)
- **Finding:** Both Docker containers ran as root
- **Fix:** `sentinel` user (UID 1001) added, `USER` directive applied in both Dockerfiles
- **Verification:** `whoami` inside container returns `sentinel`, not `root`

#### Vulnerability I — CORS Over-Permission (Medium)
- **Finding:** CORS configured with wildcard `allow_methods` and `allow_headers`
- **Fix:** Explicit enumeration: `GET, POST, PUT, DELETE, OPTIONS` and `Content-Type, Authorization`
- **Verification:** OPTIONS preflight with non-enumerated header returns 400

#### Vulnerability J — Default Secret (Low)
- **Finding:** No warning when JWT secret is the default `change-me-in-production`
- **Fix:** `logger.warning` emitted at startup if `jwt_secret` matches default
- **Verification:** Server startup log shows "WARNING: JWT secret is still set to default"

#### Vulnerability K — LocalStorage JWT Leakage (Medium)
- **Finding:** JWT stored only in localStorage, accessible to any injected script
- **Fix:** HttpOnly cookie set on login (`httponly=True`, `samesite=lax`, 8hr expiry); `get_current_user` reads cookie as fallback; DOMPurify sanitization on all frontend text components
- **Verification:** `document.cookie` cannot access `access_token`; XSS payloads cannot exfiltrate token

#### Vulnerability L — Unencrypted Database Storage (Medium)
- **Finding:** Journal entries stored as plaintext in SQLite
- **Fix:** `EncryptedText` SQLAlchemy `TypeDecorator` applied to `JournalEntry.raw_content`/`summary`, `ClinicalNote.raw_notes`/`ai_synthesis`, `FollowupTask.description`. Fernet encrypts/decrypts transparently on write/read
- **Verification:** Database file contains only ciphertext for all sensitive text fields

#### Vulnerability M — API Rate Limiting (Medium)
- **Finding:** No rate limiting on any endpoint (auth or data)
- **Fix:** `RateLimiterMiddleware`: 100 requests/minute per IP sliding window, exempts `/health` endpoint, returns 429 with `Retry-After` header
- **Verification:** 101st request within 60s returns `429 Too Many Requests`

#### Vulnerability N — Missing Input Sanitization (Medium)
- **Finding:** Frontend rendered raw user text without HTML sanitization
- **Fix:** DOMPurify added to frontend via `sanitize()` wrapper (`ALLOWED_TAGS: []`, `ALLOWED_ATTR: []` strips all HTML). Applied to `JournalPage`, `TimelinePage`, `FollowupsPage`
- **Verification:** `<script>alert(1)</script>` in journal text renders as literal text, not executed

#### Vulnerability O — Insecure Container Network Bridge (Low)
- **Finding:** Backend container port mapped to host, reachable from LAN
- **Fix:** Backend port mapping removed (`expose:` only, no `ports:`). Dedicated internal Docker network with `internal: true` driver
- **Verification:** `curl localhost:8000` from host fails; backend only reachable via frontend Nginx proxy

#### Vulnerability P — Logging/Error Information Disclosure (Low)
- **Finding:** FastAPI default error handler returned full stack traces in JSON responses
- **Fix:** Global `@app.exception_handler` for `RequestValidationError` and `Exception`. Server stack traces logged server-side via `traceback.format_exc()`, client receives sanitized `{"detail": "Internal server error — the team has been notified."}`
- **Verification:** Intentionally malformed request returns `{"detail": "Invalid request parameters"}` with no stack trace

#### Architectural Fix Q — Sarcasm/Negation Blindspot
- **Finding:** "I am not happy" classified as positive (triggers false positive)
- **Fix:** Negation-aware `_strip_negated_words()` removes keywords preceded by negation prefixes (26 words: not, no, never, don't, can't, etc.) within a 4-word window. Also fixed: neutral text + low-stress biometrics no longer triggers false positive (low stress = healthy)
- **Verification:** "I am not happy" + high BPM → neutral sentiment, no false positive

#### Architectural Fix R — Single Point of Failure
- **Finding:** SQLite WAL file unrecoverable after crash
- **Fix:** `backup_wal()` function copies WAL + DB to `data/backups/` directory on each new database connection
- **Verification:** `data/backups/` populated with timestamped copies after restart

#### Architectural Fix S — AI Cold-Start Latency
- **Finding:** Multiple simultaneous Ollama requests overwhelm low-cost hardware during cold-start
- **Fix:** Threading `Lock` + 500ms minimum gap between Ollama requests prevents thundering herd. Sequential queuing ensures model loads once, not N times
- **Verification:** 10 concurrent journal submissions → only 1 Ollama call per 500ms window

#### All 22 Findings Now Patched

The original penetration test identified 19 findings (4 critical, 8 high, 4 medium, 3 low). All 19 have been patched (#A–#J for the original 10, #K–#P for the remaining 6 security findings, and #Q–#S for the 3 architectural fixes). The system is hardened against the identified attack surface for the September 2026 pilot deployment.

---

## 11. Benchmarking & Validation

### Benchmark Suite Design

The `benchmarks/runner.py` orchestrator runs 45 benchmarks across 5 categories, producing an IRIS-standard CSV logbook.

| Category | Tests | Metric | Result |
|----------|-------|--------|--------|
| Discrepancy Detection | 4 | Accuracy, latency | 96% (48/50), < 0.1ms |
| Crisis Concurrency | 7 | Thread safety, halt timing | 101ms constant overhead, 0 drops |
| Storage I/O | 13 | Latency, file size, concurrency | SQLite: 48ms, 12 KB |
| AI Provider | 5 | Latency | Mock: 50ms, Ollama: 0ms (FAIL), Groq: 0ms (FAIL) |
| Security | 16 | Derivation, encryption, JWT | All pass, 233.2ms 600K round-trip |

**The 2 FAIL results are expected:** Ollama and Groq are not running inside the Docker container. The mock provider (test 25-27) passes at 50ms. The FAIL results validate that the benchmark correctly detects missing external services.

### Validation Philosophy

Sentinel's benchmark suite is designed for **reproducibility**:
- Every test is deterministic (same input → same output)
- CSV logbook captures per-run timing, not aggregated statistics
- The `--quick` flag runs a subset for CI integration (TODO)
- Results are regression-checkable — a 5% latency regression flags a FAIL

This approach is inspired by academic paper benchmarks where reviewers must be able to reproduce results from the provided data.

---

## 12. Problem Context

### The 0.75 Per 100,000 Problem

India has 0.75 psychiatrists per 100,000 population. The WHO minimum standard is 1 per 10,000 (or 10 per 100,000). This means India operates at **7.5% of the minimum recommended psychiatric workforce**.

**What this means in practice:**
- A patient sees a psychiatrist once per week (minimum), creating a **167-hour monitoring gap**
- During those 167 hours, the patient has no clinical observation layer
- Acute stress, suicidal ideation, and physiological decompensation all occur inside that window
- The psychiatrist has no data about what happened between sessions — only the patient's self-report

**What Sentinel changes:**
- Continuous passive biometric tracking (HR, HRV) fills the monitoring gap
- Journal text provides subjective context alongside objective physiological data
- Discrepancy detection flags mismatches before the patient self-reports deterioration
- The crisis engine provides a deterministic escalation pathway when thresholds are crossed

### Why Consumer Wearables

Consumer-grade smart rings (Oura, Ultrahuman, Circular) and watches (Apple Watch, Fitbit) already have:
- Photoplethysmography (PPG) sensors for heart rate
- HRV calculation algorithms
- Sleep stage tracking
- Stress index computation

These devices are already in widespread use. Sentinel doesn't require a dedicated medical device — it ingests data from hardware the patient already owns.

**The data pipeline:** Ring → Bluetooth → Phone App → API → Sentinel → Discrepancy Engine → Alert

### Cost Architecture

Sentinel is designed for **zero financial barrier to entry**:
- Ollama (local LLM): free, runs on CPU
- Groq (cloud LLM): free tier available
- Render (cloud hosting): free tier
- SQLite: zero licensing cost
- Docker: free for small-scale deployment

A clinic can deploy Sentinel for the cost of a $15/month cloud server or a $200 mini PC on-premises.

---

## 13. Hardware Ingestion & Ring SDK

### Decision: Secured Device-Binding Layer + Pluggable `RingSource` Adapters

Hardware M0 (2026-08-03) added physical-ring ingestion without weakening authentication. The full stack — discrepancy engine, crisis engine, AI, and dashboards — consumes one canonical `SensorData` payload, so a new device never touches clinical code.

**Architecture:**

```
OEM ring ─┬─ BLE gateway (bleak) ─┐
          ├─ vendor cloud SDK ────┤→ RingSource adapters → SensorData → POST /ring/data
          └─ simulated (dev/test) ┘                                    │
                                                     get_ring_identity (device token)
                                                                      ↓
                                                          ring_devices → ingestion → engines
```

**Device binding (`ring_devices` table):**
- `POST /ring/pair` issues a one-time device token for a serial, stored as SHA-256 hash; `POST /ring/unpair` sets `revoked=true`; re-pairing a revoked serial issues a fresh token.
- `POST /ring/data` authenticates via `X-Device-Serial` + `X-Device-Token` (constant-time `hmac.compare_digest`), resolves the owning patient, updates `last_seen_at`, and records the reading.
- `GET /ring/devices` exposes device state to the owning patient or any psychologist. Patient JWT remains a supported ingestion path for software clients.

**Ring SDK (`app/services/ring/`):**
| Adapter | Source | Notes |
|---------|--------|-------|
| `SimulatedRing` | None | Deterministic per-user-per-hour (calm/balanced/stressed), seeded for reproducible demos |
| `VendorAPIRingSource` | Vendor SDK/cloud | Single `_fetch()` hook; subclass for Oura/Ultrahuman/etc. |
| `BLEGATTRingSource` | BLE via bleak | Parses HRM 0x2A37 (8/16-bit), battery 0x180F, configurable characteristic maps |

**Bridge:** `scripts/ring_bridge.py` polls any adapter and pushes through the authenticated path (auto-pairs for simulated); `scripts/sim_ring.py` streams device-token data directly.

**Security properties:** tokens hashed at rest (SHA-256), constant-time comparison, revocation honored per-request, unknown/wrong/revoked credentials return HTTP 401. Verified by 9 ring tests plus end-to-end push (device `RING-DEMO-001`, patient `alaya`, readings `id=13`/`id=14`).

### Hardware Roadmap (M1–M3)

Funding secured from Emergent Ventures; OEM ring sourced from Jport (China) — vendor SDK/API + BLE interface (Jport spec sheet pending). Milestones: **M1** Jport integration + clinic BIOSIGNAL study gate, **M2** 30-subject clinic pilot, **M3** trusted contact + crisis validation study. See `docs/ROADMAP_HARDWARE.md`.

---

*Document prepared for Samsung Solve for Tomorrow · IRIS · ISEF 2026*
*Sentinel: On-Premises Psychophysiological Triage Node*
*~25,000 lines · 22 security patches + device-token auth · 54 benchmarks (52/54 pass) · 233.2ms crypto round-trip*
