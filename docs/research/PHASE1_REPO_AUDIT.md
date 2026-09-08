# Phase 1 & 2 — Sentinel Repository Audit + Evidence Map

Status: COMPLETE (Phase 1 & 2 of the research directive)
Date: 2026-09-01

---

## 1. Scope and Method

This document records a code-verified audit of the Sentinel repository. Every
classification below was checked against the actual implementation (source
files, benchmarks, tests, evaluation scripts, CI), not against prose docs.

Classification legend (per directive §1):
- [IMPLEMENTED]      present in code and reachable at runtime
- [EXPERIMENTALLY TESTED] measured by a hosted benchmark/tests
- [SIMULATED]        synthetic / mock / compressed-time — not real-world
- [EXTERNALLY VALIDATED] verified against external/real data or an external reviewer
- [PARTIALLY IMPLEMENTED] scaffolding exists, real path not complete
- [PLANNED]          designed but not fully built
- [UNSUPPORTED]      claimed but not present in code

---

## 2. Component Inventory & Status

### 2.1 ML / Text Analysis
| Component | Status | Evidence location |
|---|---|---|
| Emotion classifier (28-label, TF-IDF+OneVsRest LogReg) | [IMPLEMENTED] | `backend/app/ml/emotion_classifier.py` |
| Real GoEmotions training path (54,263 ex) | [IMPLEMENTED][EXPERIMENTALLY TESTED] | `backend/app/ml/train_goemotions.py`, metrics in `model_registry.json` |
| Synthetic-by-template fallback training path | [IMPLEMENTED] | `emotion_classifier.py:_generate_training_data()` (lines 75-443) |
| Risk engine (keyword + emotion blend, score 1-10) | [IMPLEMENTED] | `backend/app/ml/risk_engine.py` |
| Risk temporal/trend multiplier | [IMPLEMENTED] (partial path; requires >=3 recent texts) | `risk_engine.py:assess_risk_with_history` |
| Crisis policy thresholds (configurable constants) | [IMPLEMENTED] | `backend/app/ml/crisis_policy.py` |
| Discrepancy detector (text vs biometric mismatch) | [IMPLEMENTED] | `backend/app/api/discrepancy.py:_detect` |

### 2.2 Evaluation / Benchmarks
| Component | Status | Evidence |
|---|---|---|
| Discrepancy benchmark "96% acc, ~0.1ms" | [EXPERIMENTALLY TESTED] but **measures a LOCAL copy**, NOT the server function | `backend/benchmarks/test_discrepancy.py:_detect_discrepancy` + `profiles.py` |
| Held-out discrepancy eval (50 fresh) | [EXPERIMENTALLY TESTED] but labels are **derived from the same frozen rules** (circular) and use the local copy too | `backend/benchmarks/test_held_out.py` |
| Crisis concurrency stress | [SIMULATED] compressed-time standalone simulator, NOT `crisis.py` | `backend/benchmarks/test_crisis_concurrency.py` |
| Storage I/O (JSON vs SQLite) | [SIMULATED] temp-file microbench, not production DB schema | `backend/benchmarks/test_storage_scalability.py` |
| AI provider latency (Mock/Ollama/Groq) | [SIMULATED] mock default; Ollama/Groq optional live | `backend/benchmarks/test_ai_benchmark.py` |
| Security microbenchmarks (PBKDF2/Fernet/JWT) | [EXPERIMENTALLY TESTED] microbench only | `backend/benchmarks/test_security.py` |
| Golden-set regression (risk bands + emotion) | [EXPERIMENTALLY TESTED], online in CI | `backend/scripts/eval_golden_set.py`; `.github/workflows/ci.yml` |
| Backend pytest suite | [EXPERIMENTALLY TESTED] 99 pass locally | `backend/tests/` |

### 2.3 Ring / Physiological Hardware
| Component | Status | Evidence |
|---|---|---|
| Ring pairing / unpaired / list API | [IMPLEMENTED] | `backend/app/api/ring.py` |
| Sensor data ingestion (HR, HRV/RMSSD/SDNN, stress, sleep, SpO2) | [IMPLEMENTED] | `ring.py`, `models/sensor_reading.py`, `models/ring.py` |
| Input validation of sensor ranges | [IMPLEMENTED] | `core/input_validator.py` |
| Simulated ring (deterministic seeded stream) | [SIMULATED] | `services/ring/simulated.py` |
| BLE GATT ring adapter | [PARTIALLY IMPLEMENTED] — requires vendor spec/UUIDs; `bleak` optional | `services/ring/ble_gatt.py` |
| Vendor API/SDK ring adapter | [PARTIALLY IMPLEMENTED] — base class + hooks, no live vendor integration | `services/ring/vendor_api.py` |

> KEY: There is **no clinical-grade physiological validation**. Hardware is
> (a) simulated, or (b) an un-tested BLE/vendor scaffold. The paper must treat
> the physiological channel as a *prototype interface*, not measured physiology.

### 2.4 Crisis / Escalation Workflow
| Component | Status | Evidence |
|---|---|---|
| Crisis trigger / state / elapsed / acknowledge / resolve / trustee | [IMPLEMENTED] | `backend/app/api/crisis.py` |
| Auto-trigger on journal from AI worker | [IMPLEMENTED][EXPERIMENTALLY TESTED] | `app/workers/ai_worker.py`; `tests/test_journal_api.py` |
| Staged escalation (trusted-contact 30s, helpline 60s) | [IMPLEMENTED] as **configurable policy constants** | `crisis_policy.py` (NOT clinical evidence — engineering defaults) |
| Trustee portal signed/expiring links | [IMPLEMENTED][EXPERIMENTALLY TESTED] | `crisis.py:_make_trustee_link`, `tests/test_crisis_security.py` |
| Per-patient crisis rows (multi-patient) | [IMPLEMENTED][EXPERIMENTALLY TESTED] | `crisis.py:_get_or_create_state`, `tests/test_journal_api.py::test_crisis_rows_are_per_patient` |

> The 30s/60s escalation timings are **engineering constants subject to change**
> (country/regulatory adaptation). They are NOT a validated clinical protocol.
> Any paper text must say this explicitly and not frame them as evidence.

### 2.5 Security / Privacy
| Component | Status | Evidence |
|---|---|---|
| AuthN (register/login/refresh/logout) | [IMPLEMENTED] | `api/auth.py` |
| JWT + token blacklist | [IMPLEMENTED] | `core/security.py`, `core/token_blacklist.py` |
| Role-based AuthZ (patient/psychologist) | [IMPLEMENTED] | `core/dependencies.py:require_role` |
| Password policy + hashing | [IMPLEMENTED][EXPERIMENTALLY TESTED] | `core/password_validator.py`, `auth.py`, `tests/test_auth_flow.py` |
| Login rate limiting | [IMPLEMENTED] | `core/login_rate_limiter.py` |
| Field-level encryption (Fernet/PBKDF2) | [IMPLEMENTED] (partial field coverage) | `core/encrypted_fields.py` |
| Audit logging + event store | [IMPLEMENTED] | `services/audit.py`, `events/subscribers/` |
| Local-first AI (Ollama default, Groq gated) | [IMPLEMENTED] | `ai_service.py`, `config.py:allow_cloud_ai` |

---

## 3. FLOW OF THE ACTUAL PIPELINE (verified)
```
journal text
   → ai_service.summarize_journal()
      → emotion_classifier (TF-IDF + LogReg)  [deterministic, local]
      → risk_engine.assess_risk_with_explainability()  [keyword + emotion blend]
      → optional LLM summary (Ollama local / Groq gated) w/ echo guard + JSON parse
   → persisted; risk → notification / auto-trigger via ai_worker
ring sensor data
   → POST /ring/data  → validated → stored (HR/HRV/stress/sleep/SpO2)
discrepancy
   → POST /discrepancy/check  → rules compare text sentiment vs bio stress
```

---

## 4. Evidence Map (claim → experiment → result → gap)

### Claim 1: "Emotion classifier trained on real GoEmotions"
- Implementation: `train_goemotions.py`
- Experiment: official train+val fit / official test eval (leak-free since audit F5); formerly 80/20 re-split of merged splits (leaked)
- Result (registry, leaked): micro-F1 0.465, macro-F1 0.412, samples-F1 0.490
- Result (clean, official test): micro-F1 0.464, macro-F1 0.405, samples-F1 0.495
- Type: ENGINEERING + EXTERNAL DATASET (real labels), but **self-reported holdout**, no k-fold, no CI comparison, no calibration
- Gap → research: absolute performance is modest; this is a *reproducible baseline measuring point*, not a claim of clinical accuracy.

### Claim 2: "96% discrepancy accuracy, ~0.1 ms"
- Implementation: benchmark uses **its own local `_detect_discrepancy` copy** (`test_discrepancy.py:11`), NOT server `discrepancy.py:_detect`.
- Divergence verified: the benchmark local function has an EXTRA rule
  `negative + moderate → True` (line 125) that the server `_detect` does NOT
  have (server only flags: pos+high, neg+low, neutral+high, neg+... ). 
  => The 96% figure does NOT characterize the deployed detector.
- Held-out labels are **derived from the same frozen rules** → circular; tests rule-consistency, not generalization.
- Type: SIMULATION/self, NOT externally validated. Overclaim risk: HIGH if quoted verbatim.

### Claim 3: "Crisis engine 30s/60s staged protocol, halt works"
- Implementation: configurable policy constants (`crisis_policy.py`); real `crisis.py` mostly poll-based (`_get_or_create_state`, `_handle_escalation` on `/elapsed`).
- Experiment: concurrency benchmark is a **standalone simulator** with compressed time (TIME_FACTOR=20) and its own `CrisisSimulator` class — does not exercise `crisis.py`.
- Real-world timings of the deployed engine are NOT measured end-to-end.
- Type: PARTIALLY SIMULATED. The halt/escalation state machine is real in code, but the 30/60s firing is not empirically validated in the real service.

### Claim 4: "99/99 tests pass" (engineering)
- True locally (99 passed). CI green. Type: ENGINEERING EVIDENCE.

---

## 5. What is REAL vs SIMULATED vs PLAUSIBLE (high-level)

REAL (deterministic, reproducible, in-repo):
- TF-IDF emotion classifier + risk engine (rule + learned blend)
- Rule-based discrepancy logic (server `_detect`)
- Crisis state machine, per-patient rows, escalation config
- AuthN/AuthZ, rate limiting, audit, encryption scaffolding
- Golden-set regression gate (CI)

SIMULATED / NOT EXTERNALLY VALIDATED:
- The benchmark figures quoted in prose docs (esp. "96%", latency, storage)
- Ring = simulated stream or scaffold adapters; NO clinical physio validation
- Crisis 30/60s timings as clinical protocol

UNSUPPORTED / would-overclaim if claimed:
- Clinical effectiveness, diagnostic capability, treatment effect
- Generalization to real patients, generalizability beyond tested inputs

---

## 6. Existing Datasets / Data Sources
- GoEmotions (simplified, 28 labels) — real, external, used for training.
- Golden set — 10 hand-written risk cases + 4 emotion cases (all synthetic text).
- Discrepancy profiles — 50 hand-authored synthetic `(text, bpm, hrv)` triples, labels hand-assigned per the authors' intended rules.
- Held-out — 50 more hand-authored synthetic triples, labels assigned FROM the rules.
- Journal AI bench entries — 5 base templates repeated/noised (synthetic).
- Simulated ring — deterministic pseudo-random per user/hour.
- NO real patient text, NO real physiological recordings, NO clinician-labeled clinical corpus beyond GoEmotions.

---

## 7. Existing Experiments + Results Summary (as actually measured)
1. Emotion model: micro-F1 0.464, macro-F1 0.405 (real GoEmotions holdout,
   leak-free official test — see F5; formerly reported 0.465/0.412).
2. Golden-set regression: PASS in CI (rule consistency).
3. Discrepancy "accuracy": self-consists on hand-built profiles (see §4 claim 2 caveat).
4. Crisis concurrency: standalone simulator, halt logic OK in simulation.
5. Storage: JSON vs SQLite temp-file microbench (no production-schema effect).
6. AI latency: mock default; live results only if Ollama/Groq present.
7. pytest: 99/99.

---

## 8. Confirmed Flaws found during audit (to fix before experiments)
F1. Discrepancy benchmark tests a local copy whose logic DIVERGES from the
    deployed server detector (extra `neg+mod` rule). Fix: refactor benchmarks
    to import and call the real `app.api.discrepancy._detect` (or the single
    source of truth), and reconcile the rule sets.
F2. Held-out "generalization" is circular (labels derived from the same rules).
    Fix: the paper must present it as a *consistency* test, not generalization;
    better, build a genuinely independent held-out with manual labels.
F3. AI-benchmark "Mock" is a fake sleep; do not present mock latency as system latency.
F4. docs prose overstates figures (esp. discrepancy %, and 30s/60s as protocol).
    Fix: align wording with evidence classes.

---

## 9. DECISIVE SCIENTIFIC FINDING (post-audit, flaw fixes applied)
The discrepancy detector (`app/api/discrepancy.py:_detect`) is a **purely
rule-based, deterministic function** — no learned component. Its perceived
"accuracy" is measured ONLY against hand-authored labels that encode the same
rules, so agreement is circular by construction (~100% once labels are aligned).
It is a *consistency/regression* result, NOT a measure of detection quality or
generalization. It cannot, on its own, answer a meaningful research question.

By contrast, the **emotion classifier** is the ONE component with:
- a real, externally-grounded label source (GoEmotions, 48,836 human-labelled training examples),
- a non-circular, reproducible evaluation (official held-out test, micro-F1 0.464 / macro-F1 0.405, leak-free per F5),
- measurable risk implications (its probabilities propagate into the risk engine).

=> The most defensible research question will center on the LEARNED emotion
   model and how its probability outputs propagate into the (deterministic)
   risk-scoring and (rule-based) discrepancy layers — where real data and
   non-circular measurement exist.

## 10. Flaw fixes applied during audit (F1/F2)
F1. FIXED — `backend/benchmarks/test_discrepancy.py` now imports and calls the
    deployed `app.api.discrepancy._detect` instead of a divergent local copy.
    (Local copy had an extra `negative+moderate → True` rule the server lacked.)
F2. FIXED — `backend/benchmarks/test_held_out.py` labels realigned to the
    authoritative server rule (negative+moderate → False); previously encoded
    a rule the shipped detector does not implement. Both the 50-profile set and
    the server already used negative+moderate → False.
    NOTE: this makes the held-out measure consistency with the shipped rules,
    NOT generalization. The paper must state this explicitly.
F3. NOTED (not changed) — AI-benchmark "Mock" provider is a fixed 50ms sleep;
    mock latency is not real system latency.
F4. FIXED (Sep 2026) — prose figures reworded to evidence classes across
    docs/ (JUDGE_QA, TECHNICAL_DESIGN, proposal_500, ENGINEERING_LOGBOOK):
    discrepancy "96%" reframed as rule consistency (not generalization), and
    30s/60s escalation timings explicitly tagged as product policy, not a
    validated clinical protocol.
F5. FIXED (Sep 2026) — validation leakage in the training pipeline.
    `train_goemotions.py` merged all three official GoEmotions splits then
    re-split 80/20 (seed 42), sweeping ~80% of the official test rows (4,346 of
    5,427) into training. This inflated in-domain micro-F1 to 0.610.
    Fix: train on official train+validation (48,836) only; evaluate on
    official test (5,427). Retrained, redeployed `emotion_model.pkl` (new MD5
    9a8d157c6e42706c43b354df6d1025fc), registry updated. Leak-free in-domain
    is micro-F1 0.464 / macro-F1 0.405 / samples-F1 0.495 — which matches the
    old registry numbers, confirming the model was NOT overfitting to leaked
    rows and the registry figure was honest by chance. All research experiments
    re-run from the clean artifact (see PHASE8_9_RESULTS.md).

## 11. What This ENABLES as Research (initial directions)
- LEARNED emotion classifier: real, reproducible, externally-grounded metric
  (GoEmotions holdout) — the strongest scientific footing.
- Risk-score fusion: emotion-probability-weighted + keyword blend; quality
  depends on the emotion model's calibration; measurable against GoEmotions
  (non-clinical, social-media domain).
- Discrepancy layer: fully rule-based; honest role is a deterministic policy,
  not a learned result. Usable as a *policy/framework* contribution (how to
  reconcile subjective vs objective channels) provided it is labelled as
  rule-based and non-validated clinically.

Full candidate gap analysis (with literature) is Phase 3; this report is the
factual floor the research must respect.

---

## 12. Next Phase Requirements
Phase 3 (research-gap analysis) needs: literature search across multimodal
mental-health risk-signal fusion, text+physiological discrepancy (Objective vs
Subjective), emotion-recognition evaluation in clinical/social text, and
XAI/explainability in mental-health support systems — then 5-8 candidate gaps
mapped to the above evidence map and the Phase 4 scoring rubric.
