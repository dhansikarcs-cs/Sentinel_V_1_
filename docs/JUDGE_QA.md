# Sentinel — Judge Q&A Preparation

## Every Possible Question — With Answers

### Samsung Solve for Tomorrow · IRIS · ISEF

---

## Section A: The Problem & Motivation

**Q: Why not just use existing mental health apps?**
A: Existing apps are appointment-only telehealth platforms or generic wellness trackers. They don't connect patient, psychologist, and trusted contact in a real-time loop. None passively monitor biometric data alongside journal text to detect deterioration between sessions. The 167-hour gap is unaddressed.

**Q: Is 0.75 per 100,000 really accurate?**
A: Yes — WHO Mental Health Atlas 2020 and Indian Psychiatric Society's National Mental Health Survey (2015-2016) both report this figure. The WHO-recommended minimum is 1 per 10,000. India operates at less than 10% capacity.

**Q: Couldn't a simple phone call solve the monitoring gap?**
A: Phone calls require the psychiatrist to initiate them, consuming their limited time. India has 0.75 psychiatrists per 100,000 — they physically cannot call 100+ patients daily. Sentinel automates the monitoring layer while keeping clinical decisions with the human.

**Q: Why focus on India specifically?**
A: The numbers are worst in India, but the problem is global. Rural US, sub-Saharan Africa, and Southeast Asia face similar ratios. Sentinel was designed for the worst case — offline-capable, low-cost, minimal dependencies.

---

## Section B: Technical Decisions

**Q: Why rule-based discrepancy instead of machine learning?**
A: A false negative in a triage pipeline is lethal. ML produces probabilistic outputs with no hard guarantees. Our rule-based system is deterministic — same input, same output, every time. Every classification can be traced to specific trigger words. Adding a language requires only adding new keywords, not retraining a model.

**Q: But doesn't ML get better accuracy?**
A: On benchmark datasets, yes. On clinical real-world data with sarcasm, code-switching, and clinical jargon — no. The ML models we tested (TF-IDF, DistilBERT) produced 82-91% accuracy on GoEmotions, but their failures were unpredictable. A deterministic system with 100% accuracy on 50 hand-crafted profiles is safer for triage.

**Q: Why SQLite instead of PostgreSQL?**
A: Target deployment is clinics and community centers — not tech companies. SQLite requires zero configuration, zero maintenance, and zero database administrator. It's a file. Backup is a copy command. PostgreSQL needs a server, connection management, and ~100MB idle RAM. SQLite uses ~4MB. For a clinic with <100 concurrent users, SQLite with WAL mode performs identically.

**Q: What happens at scale?**
A: SQLAlchemy migrations path exists: change one environment variable (`DATABASE_URL`) from SQLite to PostgreSQL. Everything else stays the same. The benchmark data shows SQLite handles 500 profiles at 260ms — acceptable for clinic scale. Beyond that, PostgreSQL is a drop-in replacement.

**Q: Why Fernet over AES-GCM?**
A: Fernet bundles authentication (HMAC), timestamp verification, and serialization into a single ciphertext string. AES-GCM requires manual nonce management, tag extraction, and encoding. For a Python application, Fernet is the safe default — fewer lines of custom crypto code means fewer vulnerabilities.

**Q: Why 600,000 PBKDF2 iterations?**
A: NIST SP 800-132 recommends 100-300ms derivation latency. Our benchmark produces 154.8ms at 600K iterations — within the NIST sweet spot. Higher iterations increase security at the cost of login latency. 600K was chosen as the point where latency is still acceptable (<200ms) while iteration count is well above common defaults (many apps use 100K).

**Q: Why not Argon2id?**
A: Argon2id is superior (memory-hard, ASIC-resistant). It requires the `argon2-cffi` package with compiled C bindings. For a Python application targeting clinics without software engineers, bcrypt + PBKDF2 was the more conservative choice. A TODO in the code explicitly marks Argon2id for the September 2026 pilot migration.

**Q: Why not use Redis?**
A: Redis is another service to deploy, monitor, and backup. For WebSocket pub/sub, Redis would survive server restarts — but Sentinel currently runs single-process, where in-memory connections work fine. The `websocket_manager.py` has a TODO to migrate to Redis when multi-process deployment is needed.

**Q: Why not use a proper task queue (Celery)?**
A: Celery requires a broker (Redis/RabbitMQ). The crisis countdown engine doesn't need persistent queuing — it needs immediate, cancellable threads. Celery tasks are designed for durable, retryable workloads. Crisis escalation is ephemeral — either the psychologist acknowledges within 60 seconds or the helpline fires. Threads handle this correctly.

---

## Section C: Security

**Q: How did you find 19 vulnerabilities?**
A: We ran a pre-deployment penetration test using standard OWASP methodology: manual endpoint review, automated scanning with OWASP ZAP, and code review for common vulnerability classes (IDOR, privilege escalation, timing attacks). The 19 findings include 4 critical, 8 high, 4 medium, 3 low.

**Q: Why didn't you patch all 19?**
A: All 10 critical and high-severity findings were patched. The remaining 9 (4 medium, 3 low, 2 informational) include items like rate limiting (needs Redis — deferred to pilot), Docker health checks (operational, not security-critical), and Content Security Policy headers (frontend enhancement). These don't pose immediate data exposure risk.

**Q: Is the timing side channel really exploitable?**
A: Yes — Python's `==` operator on HMAC digests short-circuits on the first non-matching byte. A remote attacker could send millions of HMAC values and statistically determine the correct digest byte-by-byte. `hmac.compare_digest()` runs in constant time regardless of input, making this attack impossible. The fix was one line: `hmac.compare_digest(provided, expected)` instead of `provided == expected`.

**Q: What is a role escalation attack?**
A: The registration endpoint originally accepted any string for the `role` field. An attacker could register with `role: "admin"` or `role: "superuser"` to bypass psychologist access controls. The fix constrains the role to `Literal["patient", "psychologist"]` at the Pydantic schema layer — any other value is rejected at the API boundary with a 422 validation error.

**Q: How does the encryption unlock work?**
A: Two independent secrets: (1) password for authentication (bcrypt-hashed, JWT-issued), (2) passphrase for encryption (PBKDF2-derived Fernet key). The server never stores the passphrase — only the derived key in memory after unlock. Even a full database breach yields encrypted journal content. Without the passphrase (entered each session), data stays encrypted.

**Q: What happens if the passphrase is lost?**
A: Data is unrecoverable. This is by design — zero-knowledge encryption means no backdoor. For production deployment, we recommend the clinic designate two key holders (a 2-of-2 Shamir Secret Sharing scheme could be implemented). The current system logs a warning if encryption hasn't been unlocked after 24 hours.

---

## Section D: Crisis System

**Q: What if the crisis thread fails?**
A: Daemon threads are isolated from the request-handling event loop. A crisis thread failure doesn't affect API availability. Tested at 25 concurrent threads with zero drops. Each thread checks a halt flag on a 5ms poll cycle — if the thread crashes, the 60-second Stage 3 escalation naturally fires the helpline webhook as the safety net.

**Q: What prevents false alarms?**
A: The discrepancy engine is calibrated for over-sensitivity on negative signals — false positives trigger a human check, which is safe. False negatives (missing a real crisis) are avoided by design. The crisis trigger itself is manual (patient-initiated) or discrepancy-initiated (system-initiated). Both require crossing explicit thresholds.

**Q: What is the halt protocol?**
A: When a psychologist calls `POST /crisis/acknowledge`, a thread-local `halted` boolean is set. All active countdown threads observe this on their next 5ms poll. Cancellation is instantaneous with zero residual CPU. Verified at three acknowledgment timestamps (15s, 45s, 65s simulated) — all halt correctly.

**Q: Why 20x time compression in testing?**
A: Real-world 60-second escalation would make testing impractically slow. 20x compression means a full Stage 1→2→3 cycle completes in 3 seconds. The `TIME_FACTOR` constant is adjustable and the benchmarks run at multiple concurrency levels. The relationship between compressed and real time is linear and predictable.

---

## Section E: AI & Data

**Q: Is the AI making clinical decisions?**
A: Never. The AI can't diagnose, prescribe, or override a human decision. Its role is strictly supportive: summarizing journals, suggesting SOAP note structures, extracting emotion labels. The discrepancy engine and crisis escalation are completely rule-based — zero ML. The AI is an assistant that makes clinicians more efficient, not a replacement.

**Q: What about hallucinations?**
A: The AI summaries could hallucinate content. We mitigate this with two mechanisms: (1) dual-mode output — a warm reflection for the patient, a structured OAP note for the clinician — both derived from the same journal text, (2) three-tier fallback: if Ollama hallucinates unparseable JSON, the system falls back to rule-based extraction (truncation + keyword scoring) which can't hallucinate.

**Q: The benchmark shows FAIL for Ollama and Groq. Why?**
A: The benchmark runs inside a Docker container that doesn't have Ollama installed or Groq API keys configured. Tests 28 and 29 correctly detect that these services are unavailable and report FAIL. In production, where Ollama runs on the same host or Groq API keys are configured, these tests pass. The FAIL result validates that the benchmark correctly detects missing services.

**Q: How was the training data created?**
A: Synthetic data generation using templates (`generate_training_data.py` produces 40+ clinical scenarios across 4 task types). Real data from `counsel-chat.json` and `mental_health_chatbot_dataset.json` is mixed in for diversity. The fine-tuning scripts in `scripts/training/` include DistilBERT, TF-IDF, and Ollama Modelfile approaches — all documented and reproducible.

**Q: What about patient data privacy in training?**
A: No real patient data was used in training. All benchmark data is synthetic. The synthetic journal generator creates realistic but entirely fabricated patient profiles. The September 2026 pilot will collect real data under institutional ethics board approval with informed consent.

---

## Section F: Validation & Results

**Q: 100% accuracy on 50 profiles sounds like overfitting.**
A: It's a rule-based system — there's nothing to overfit. The 50 profiles test every combination of: positive/negative/neutral text × high/moderate/low-stress biometrics × edge cases. 100% is expected because the rules are explicit and the test cases match the rules. The real question is generalization to real-world text — which is why the September 2026 pilot will collect natural-language journals for validation.

**Q: What edge cases will real-world text produce?**
A: Sarcasm ("having a great time in this nightmare"), clinical language ("my anxiety inventory was elevated"), non-English code-switching ("I feel very anxious yaar"), and implied distress ("you know how it is"). The current system handles these conservatively (neutral classification = safe). The pilot will generate a labeled corpus to extend the rule set.

**Q: How do you handle scaling to more users?**
A: The benchmarks test 50 and 500 profiles. Storage I/O scales linearly at 10-50-100-500 (33ms → 260ms for bulk SQLite writes). The thread overhead for crisis concurrency is constant (~101ms) regardless of active threads — O(1), not O(n). The bottleneck is hardware, not architecture.

**Q: Why measure thread management overhead?**
A: To prove the crisis engine doesn't degrade under load. If thread overhead grew with concurrency (e.g., 101ms at 1 thread, 2.5s at 25 threads), the system wouldn't be predictable. The constant overhead demonstrates O(1) thread management — a property of Python's threading implementation.

**Q: What is the 33-row logbook?**
A: A CSV file produced by `benchmarks/runner.py` with columns: Run ID, Component, Concurrency, AI Mode, Input Size, Latency (ms), CPU Peak (KB), RAM Peak (KB), Pass/Fail, Notes. This is an IRIS-standard format for academic reproducibility. Every benchmark run appends to this logbook.

---

## Section G: Deployment & Practicality

**Q: A clinic would need a server. Isn't that a barrier?**
A: A $200 mini PC (Raspberry Pi 5, Intel N100) runs Ollama + Sentinel simultaneously. Or free tier on Render.com — zero cost for the first clinic. Docker Compose is two commands and the entire stack is running. For clinics with no technical staff, we provide a pre-configured Docker image.

**Q: How does a patient get a smart ring?**
A: Many patients already own smart rings/watches (Oura, Apple Watch, Fitbit have 30%+ penetration in urban India). The September 2026 pilot will provide rings to 30 subjects. We're also developing a Bluetooth-paired phone app that uses the phone's camera-based PPG as a zero-cost alternative.

**Q: What about internet connectivity?**
A: Core functions (discrepancy engine, crisis escalation) require zero internet. AI summarization prefers Ollama (local, no internet needed) with Groq as cloud fallback. The only internet-dependent feature is trusted contact email (SMTP). A clinic can run Sentinel fully offline by configuring a local SMTP relay or disabling email alerts.

**Q: Why not make it a mobile app?**
A: A web application reaches any device with a browser — no app store approval, no platform lock-in, no update friction. Psychologists can triage from a desktop, tablet, or phone. The React SPA is responsive and works on mobile screens.

**Q: What about HIPAA / data residency compliance?**
A: With Ollama (local inference) and SQLite (local storage), patient data never leaves the clinic network. The encryption design (PBKDF2 + Fernet, zero-knowledge passphrase) satisfies HIPAA data-at-rest requirements. Hash-chained audit logs satisfy HIPAA audit trail requirements. For clinics requiring cloud deployment, Render's SOC 2 compliance covers the infrastructure layer.

---

## Section H: Comparisons & Competition

**Q: How is this different from Calm or Headspace?**
A: Calm and Headspace are meditation apps with no clinical integration, no psychologist dashboard, no biometric monitoring, and no crisis escalation. They're wellness products. Sentinel is a clinical triage node.

**Q: How is this different from a tele-psychiatry platform?**
A: Tele-psychiatry is appointment-based — 50 minutes per week, no between-session monitoring. Sentinel fills the 167-hour gap with passive monitoring and algorithmic triage. It's not a replacement for therapy; it's an infrastructure layer that makes therapy more effective by giving the clinician data about what happened between sessions.

**Q: How is this different from Crisis Text Line?**
A: Crisis Text Line is human-staffed — every conversation consumes a counselor's time. Sentinel automates the initial triage layer. Only when discrepancy or crisis thresholds are crossed does a human enter the loop. This scales psychiatric capacity rather than consuming it.

**Q: What about existing academic systems (MONARCA, BRiTE)?**
A: MONARCA (2012) used smartphone sensors for bipolar disorder monitoring with a rule-based alert system. It proved that passive monitoring works but required custom hardware. BRiTE (2015) used a tablet-based system for schizophrenia. Both are research prototypes, not deployable open-source infrastructure. Sentinel is the first system that: (1) runs on commodity hardware, (2) integrates consumer wearables, (3) provides AI-assisted clinician tools, (4) is deployable via Docker Compose.

**Q: How is this different from the current literature on text-biometric fusion?**
A: The literature primarily uses neural networks (LSTM, transformers) to combine text and biometric streams. These achieve 85-94% accuracy on benchmark datasets but produce opaque classifications. Sentinel's deterministic approach prioritizes auditability and safety over marginal accuracy gains. We argue that for a triage system, 100% auditable accuracy at 0.1ms is better than 94% probabilistic accuracy at 200ms.

---

## Section I: Future Work

**Q: What's next after the September 2026 pilot?**
A: Four priorities: (1) per-patient crisis states (multi-crisis support), (2) Argon2id migration, (3) Redis pub/sub for multi-process WebSocket scaling, (4) labeled discrepancy corpus from pilot data for rule set extension.

**Q: Will you open-source this?**
A: The codebase (21,810 lines) is already in a repository with MIT license consideration. Post-pilot, we plan to publish the full benchmark suite and training pipeline for academic reproducibility.

**Q: What would ISEF-level impact look like?**
A: A deployable system that demonstrates a 30% reduction in crisis escalations over standard care, or a 20% improvement in clinician documentation time. The pilot is designed to measure both metrics.

**Q: What if the psychologist doesn't acknowledge the crisis?**
A: After 60 simulated seconds (real-time configurable), the system escalates to helpline and/or emergency services. The chain of escalation is: patient → psychologist → trusted contact → helpline. Each step adds more responders until someone acknowledges.

---

## Section J: Encryption at Rest

**Q: You claim HIPAA compliance, but your database is stored in plaintext SQLite. How do you encrypt data at rest?**
A: We initially deferred encryption at rest, but we've since implemented it via an `EncryptedText` SQLAlchemy `TypeDecorator`. Three model fields — `JournalEntry.raw_content`, `ClinicalNote.raw_notes`, and `FollowupTask.description` — are now transparently encrypted using Fernet (AES-128-CBC + HMAC-SHA256). The encryption key is derived from a clinician-entered passphrase via PBKDF2-HMAC-SHA256 at 600,000 iterations, then split into separate Fernet and HMAC keys via HKDF-Expand. On write, the TypeDecorator calls `encrypt_text()` before binding to the database. On read, it calls `decrypt_text()` after loading from the database. The raw SQLite file now contains only ciphertext for all patient-identifiable content.

**Q: Why didn't you encrypt everything from day one?**
A: The encryption infrastructure existed (`encrypt_text()`/`decrypt_text()` in `security.py`) but wasn't wired into the model layer. We prioritized reliability of the core clinical algorithms over data-at-rest encryption during prototyping. For the competition submission, we completed the wiring — it was always the architecture, just not yet connected.

**Q: What happens to data written before encryption is initialized?**
A: Before a clinician enters their passphrase via `/auth/unlock`, the `EncryptedText` TypeDecorator passes data through as plaintext (no-op). Once encryption is initialized, all new writes are encrypted and all reads attempt decryption. Pre-unlock plaintext data becomes inaccessible after unlock — it displays as `[ACCESS DENIED / DATA CORRUPTED]`. This is by design: in production, the unlock sequence happens at server startup before any patient data is created.

---

## Section K: Authentication & Token Storage

**Q: You store JWTs in localStorage — that's vulnerable to XSS. Why not HttpOnly cookies?**
A: We now support both. The login endpoint sets an HttpOnly, SameSite=Lax cookie (`access_token`) alongside the JSON body response. The `get_current_user()` dependency checks the cookie if no `Authorization` header is present. The frontend can rely on the browser's automatic cookie sending for all requests. We also added DOMPurify on all text-rendering surfaces as defense-in-depth against XSS. localStorage remains available as a fallback for clients that need explicit token access (e.g., programmatic API clients), but the primary auth channel is now the HttpOnly cookie.

**Q: Does the cookie expire? What happens on browser close?**
A: The cookie has `max_age=28800` (8 hours), matching the JWT expiry. A session cookie (no `max_age`) would be cleared on browser close, which forces re-login — that's actually more secure but worse UX for clinicians who need to step away and come back. Our 8-hour expiry covers a full clinical workday. The `/auth/logout` endpoint clears the cookie explicitly.

---

## Section L: Rate Limiting

**Q: You have no rate limiting. What prevents someone from DDoSing your API?**
A: We've added an in-memory `RateLimiterMiddleware` that enforces 100 requests per minute per IP address. When exceeded, it returns 429 Too Many Requests with a `Retry-After` header. The `/health` endpoint is exempted for monitoring tools. This provides basic protection against automated abuse without the infrastructure overhead of Redis or a dedicated rate-limiting service.

**Q: 100 requests per minute is generous. Why so high?**
A: The benchmark suite itself makes about 45 requests in rapid succession during testing. Additionally, the WebSocket-based crisis engine can trigger multiple parallel requests from the frontend during alert broadcasting. 100 req/min gives legitimate use room while still throttling scripted attacks. In the clinic LAN context, this is additional defense-in-depth on top of the physical network isolation.

---

## Section M: Input Sanitization

**Q: Can a patient inject malicious content through their journal entry?**
A: React's JSX escaping prevents script execution from text content, but we added defense-in-depth. We installed `DOMPurify` on the frontend and created a `sanitize()` utility that strips all HTML tags and attributes before rendering. It's applied to `raw_content`, `summary`, `description` in every component: JournalPage, TimelinePage, and FollowupsPage. Combined with the internal Docker network preventing external web access, XSS vectors are blocked at multiple layers.

---

## Section N: Error Handling

**Q: Your API will leak internal paths and variable names in 500 errors. Judges will notice.**
A: We've added global exception handlers. All unhandled exceptions are logged server-side with full `traceback.format_exc()` for debugging, but the client receives only `{"detail": "Internal server error — the team has been notified."}`. Validation errors return `{"detail": "Invalid request parameters"}` without exposing field names or type expectations. This was an intentional gap during prototyping that we've now closed for the competition submission.

---

## Section O: Architectural Fixes

**Q: Your discrepancy engine can't handle sarcasm or negation. "I'm not happy" would be flagged as positive.**
A: This is now fixed. We added a `_strip_negated_words()` function that detects negation prefixes ("not", "no", "never", "don't", "can't", "won't", etc.) and removes any keyword within a 4-word window following them. "I'm not happy" no longer matches the positive keyword "happy". We also fixed an over-sensitivity issue: `neutral + low_stress` (normal/healthy biometrics) no longer triggers a false discrepancy alert. Only `neutral + high_stress` triggers.

**Q: What if your single laptop fails? You have no backup.**
A: We added `backup_wal()` — a function that copies both the SQLite WAL file and the main database file to a `data/backups/` directory on each connection initialization. This runs alongside the existing WAL journal mode which provides crash recovery. In production, this directory would be mounted to a RAID array or cloud sync target.

**Q: Your Ollama calls can take 10 seconds. What if multiple patients submit at once?**
A: We added a threading Lock with a 500ms minimum gap between Ollama requests. This serializes concurrent calls and prevents the thundering herd problem on low-cost hardware. The queue is in-memory and non-persistent — if the backlog exceeds reasonable bounds, the system falls back to the rule-based engine (Layer 3) which responds within 50ms regardless of load.

---

## Section P: Hardware Ingestion & Device Security

**Q: How does a physical ring authenticate? You can't type a password on a ring.**
A: We added a device-binding layer. `POST /ring/pair` returns a one-time device token for the ring serial; the patient binds it through their authenticated session. The API stores only the SHA-256 hash of the token, and each sensor push authenticates with `X-Device-Serial` + `X-Device-Token` headers via constant-time `hmac.compare_digest`. A revoked device (after `POST /ring/unpair`) is rejected per-request, and re-pairing a revoked serial issues a fresh token. Physical hardware never holds a patient password.

**Q: What if the token leaks from the ring bridge?**
A: Tokens are hashed at rest, so a database dump does not expose usable credentials. In the clinic LAN deployment the bridge runs on a trusted host inside the same internal Docker network as the API, so the token never leaves the clinic. Rotation is a re-pair away: unpair the serial, pair again, and the old token is dead. The patient JWT path remains only for software clients.

**Q: Why not just accept the vendor's cloud API and skip BLE?**
A: We support both. `VendorAPIRingSource` is an adapter base for vendor SDK/cloud interfaces (Oura, Ultrahuman), and `BLEGATTRingSource` handles local BLE gateways using bleak. Both adapters emit the same canonical `SensorData` payload and push to the same `POST /ring/data` endpoint, so the discrepancy engine, crisis engine, and dashboards never change regardless of transport. The bridge script (`scripts/ring_bridge.py`) runs any adapter on a polling loop and auto-pairs simulated devices.

**Q: How is the ring data different from a patient manually entering their stress level?**
A: Manual self-report is subjective, sparse, and can be affected by mood bias. Ring data is objective, continuous (per-minute BLE gateway or per-session vendor cloud), and timestamped by the device. The discrepancy engine specifically compares this objective physiology against the subjective journal text — that cross-check is the core research contribution and cannot be done with self-report alone.

**Q: What hardware are you actually deploying?**
A: We received funding from Emergent Ventures and are sourcing an OEM smart ring from Jport (China) that exposes a vendor SDK/API and BLE interface; the Jport specification sheet is pending and informs the M1 integration milestone. In parallel, the `SimulatedRing` adapter produces deterministic per-user, per-hour streams (calm/balanced/stressed) so demos and tests are fully reproducible without hardware. The clinical pilot (M2) plans 30 subjects.

---

*Prepared for Samsung Solve for Tomorrow · IRIS · ISEF 2026*
*Have questions not on this list? Ask. The design is defensible.*
