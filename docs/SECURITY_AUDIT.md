# Sentinel — Security Audit Report

**Date:** 2026-09-04
**Scope:** .env, source code, Docker, git history, frontend, backup system

---

## CRITICAL — Immediate Action Required

### 1. Live credentials in .env (local only — never committed)

| Credential | Location | Risk |
|-----------|----------|------|
| Gmail SMTP password (rajendrandhansika62@gmail.com) | `.env:3` | Email account compromise |
| Gmail SMTP password (dhansika.r.cs@gmail.com) | `.env:8` | Email account compromise |
| Groq API key (`gsk_3TKVjjFNlH...`) | `.env:16` | API abuse, potential charges |
| Personal email addresses | `.env:2,4,7,9,10` | PII exposure if repo is shared |

**Status:** `.env` was NEVER committed to git (`.gitignore` works). But the file exists in the repo root. If this ZIP is shared, the credentials travel with it.

**Action:** Rotate ALL three credentials immediately:
1. Regenerate Gmail app passwords for both accounts
2. Regenerate Groq API key at console.groq.com
3. Update `.env` with new values

---

## HIGH — Fix Before Public Sharing

### 2. Default JWT secret in config

`backend/app/core/config.py:10`:
```python
jwt_secret: str = "change-me-in-production-use-a-real-secret"
```

`docker-compose.yml:8`:
```yaml
JWT_SECRET=${JWT_SECRET:-change-me-in-production}
```

**Risk:** If deployed without setting `JWT_SECRET` env var, JWT tokens use a predictable secret. Anyone can forge tokens.

**Mitigation exists:** `main.py:68` warns at startup if default is detected. But warning ≠ prevention.

**Action:** Either:
- Remove the default entirely (crash if not set) — safest
- Or keep the warning but ensure Render's `render.yaml` uses `generateValue: true` (it does)

### 3. Seed demo passwords are weak

`backend/seed_demo.py`:
```python
password_hash=hash_password("1234")  # patient
password_hash=hash_password("4321")  # psychologist
```

**Risk:** If seed data is used in any non-test environment, accounts have trivially guessable passwords.

**Action:** Mark seed data as test-only. Add a comment. Or use random passwords in seed script.

---

## MEDIUM — Should Address

### 4. Backup script S3 credentials via env vars

`backend/scripts/backup_db.py` reads S3 credentials from environment:
```
S3_ENDPOINT_URL, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY
```

**Status:** Properly uses env vars, not hardcoded. Backups are Fernet-encrypted before upload.

**Risk:** Low — but verify S3 credentials are never logged or included in error messages.

### 5. Config reads .env from relative path

`backend/app/core/config.py:38`:
```python
env_file = "../.env"
```

**Risk:** If backend is run from a different working directory, it may not find `.env` or may read the wrong file.

**Action:** Consider using absolute path or `SENTINEL_ENV_FILE` env var for production.

---

## LOW — Informational

### 6. Test credentials are test-only

`backend/conftest.py:9`:
```python
os.environ.setdefault("JWT_SECRET", "pytest-secret-not-for-production")
```

**Status:** Acceptable — test-only, never reaches production.

### 7. Frontend has no client-side secrets

No `NEXT_PUBLIC_`, `REACT_APP_`, or `VITE_` variables with secrets found.

**Status:** Clean.

### 8. Dockerfile runs as non-root

```dockerfile
RUN addgroup --system --gid 1001 sentinel && adduser --system --uid 1001 --ingroup sentinel sentinel
USER sentinel
```

**Status:** Good practice.

### 9. Device tokens are hashed

`backend/app/core/dependencies.py:64`:
```python
def _hash_device_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
```

Raw device tokens are never stored — only SHA-256 hashes. Constant-time comparison used.

**Status:** Good practice.

### 10. Groq API key validated before use

`backend/app/services/ai_service.py:96`:
```python
if not key or key == "gsk_your_key_here":
```

**Status:** Placeholder check exists. Won't accidentally call Groq with fake key.

---

## Git History Clean

| Check | Result |
|-------|--------|
| `.env` committed? | **NO** — never in git history |
| Real Groq key committed? | **NO** — only placeholder `gsk_your_key_here` in code |
| SMTP passwords committed? | **NO** |
| `.env.example` committed? | **YES** — contains only placeholders (correct) |
| Other secrets in history? | **NONE FOUND** |

---

## Encryption Coverage Map

### Which models use encryption

**7 of 20 models** use `EncryptedText` fields:

| Model | Encrypted Fields |
|---|---|
| `User` | `trusted_contact`, `contact_info`, `psych_trusted_contact` |
| `JournalEntry` | `raw_content`, `summary`, `clinical_summary` |
| `PsychJournalEntry` | `raw_content`, `summary` |
| `ClinicalNote` | `raw_notes`, `ai_synthesis` |
| `FollowupTask` | `description`, `feedback` |
| `Booking` | `contact`, `explanation` |
| `TriageEntry` | `suggestion`, `reasoning` |

### Sensitive fields NOT encrypted

**🔴 HIGH — clinical/therapeutic narrative content (✅ NOW FIXED 2026-09-04)**

| Model | Field | Status |
|---|---|---|
| `AIAnalysis` | `summary_patient`, `summary_clinical`, `explanation` | ✅ Now `EncryptedText` |
| `RiskAssessment` | `explanation` | ✅ Now `EncryptedText` |
| `RingSensorLog` | `raw_json` | ✅ Now `EncryptedText` |

These were plaintext; now encrypted. 99/99 tests pass.

**🟠 MODERATE — physiological readings (health data) — plaintext by design, see compensating control below**

| Model | Field |
|---|---|
| `SensorReading` | `heart_rate`, `rmssd`, `sdnn`, `temperature` |
| `RingSensorLog` | `bpm`, `stress`, `sleep_hours`, `spo2`, `hrv` |
| `TriageEntry` | `bpm`, `stress` |

**🟠 MODERATE — risk/scoring data — plaintext by design**

| Model | Field |
|---|---|
| `RiskAssessment` | `risk_score`, `triggered`, `confidence` |
| `TriageEntry` | `urgency_score` |

**🟠 MODERATE — emotion profile (behavioral/mental health) — plaintext by design**

| Model | Field |
|---|---|
| `EmotionResult` | all 28 emotion float columns |
| `JournalEntry` | `emotions`, `emotion_probabilities` |

**🟡 LOWER — operational/contextual**

| Model | Field |
|---|---|
| `EventRecord` | `payload`, `extra_metadata` |
| `CrisisLog` | `details` |
| `AuditLog` | `details` |
| `Notification` | `message` |

### Key findings

1. **✅ DONE:** All the highest-value narrative fields (AI clinical summaries, risk explanations, raw ring JSON) are now encrypted.
2. **Physiological numeric + risk score + 28 emotion floats remain plaintext by design.** These cannot be column-encrypted because the risk engine and longitudinal analysis compare/sort them in SQL (e.g. `stress > 70`, `bpm >= BPM_HIGH`, `sleep_hours - prev >= SLEEP_DROP_HOURS`). Column-level encryption would break the core engines.

### Compensating control for numeric fields (required before pilot)

Since numeric physiological/risk/emotion columns must stay queryable, protect them at the **database-file level** instead of the column level. Recommended (pick one):
- SQLCipher (transparent SQLite encryption), OR
- OS/volume-level encryption on the DB, OR
- Encrypted volume/container with access control

This satisfies at-rest protection for the numeric data without breaking the engines. Must be in place before any real pilot data.

---

## Summary

| Severity | Count | Status |
|----------|-------|--------|
| 🔴 Critical | 1 | `.env` credentials — rotate immediately |
| 🟠 High | 2 | Default JWT weak password in seed |
| 🟡 Medium | 2 | Backup S3 logging, config path |
| 🟢 Low | 5 | All good practices |
| ✅ Git clean | Yes | No secrets ever committed |

---

## Immediate Actions

1. **Rotate** Gmail app passwords (both accounts)
2. **Rotate** Groq API key
3. **Update** `.env` with new values
4. **Never share** the raw `.env` file — share `.env.example` only
5. **Before sharing ZIP:** verify `.env` is excluded or redacted
