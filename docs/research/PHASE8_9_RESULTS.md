# Phase 8 & 9 — Experiment Results and Statistical Analysis

Status: COMPLETE (with statistical analysis)
Depends on: `PHASE6_7_LIT_MATRIX_AND_DESIGN.md` (design locked), `PHASE5_QUESTION_SPEC.md`

---

## 0. MAJOR FLAW FOUND + FIXED DURING EXECUTION (F5: validation leakage)

The shipped training pipeline (`train_goemotions.py`) merged the official
GoEmotions train/validation/**test** splits and then took a random 80/20 split
from the whole pool (seed 42). Consequence: **4,346 of the 5,427 official test
rows (80%) were inside the training partition**. Any evaluation run against the
official test set therefore measured partly **memorised** text, not
generalisation.

Impact revealed while running E2:
- Naive in-domain micro-F1 on official test with the leaked model = **0.610** (inflated).
- The true, leak-free in-domain estimate (only the 1,081 official-test rows the
  model never saw) = **micro-F1 0.464**, macro-F1 0.429, samples-F1 0.489 —
  virtually identical to the registry's original 0.465/0.412/0.490, which is a
  *good* sign: the model was not overfitting to the memorised rows.

FIX APPLIED (backend, pushed with the research):
1. `train_goemotions.py` now trains on **official train + validation only**
   (48,836 rows) and evaluates on the **official test split (5,427 rows)** —
   no leakage possible.
2. `emotion_classifier._build_model()` (fallback path) fixed identically.
3. New clean model deployed to `emotion_model.pkl` (MD5
   `9a8d157c6e42706c43b354df6d1025fc`), registry updated with leak-free split
   metadata.

**Clean retrained model metrics (official held-out test, no leakage):**
micro-F1 **0.4642**, macro-F1 **0.4047**, samples-F1 **0.4947**.

All numbers below come from THAT clean model. D_IN = full official test split
is now genuinely held-out.

---

## 1. Experiment summary (all from shipped clean model `emotion_model.pkl`)

Datasets:
- D_IN: GoEmotions official test (5,427 rows, real human multi-hot labels).
- D_CAL: GoEmotions train+val (48,836 rows) — only to fit per-class isotonic
  calibrators for the calibrated-reference counterfactual.
- D_OUT: product's synthetic mental-health journaling templates (1,730 rows,
  single-emotion labelled, author-generated, disclosed as synthetic / NOT clinical).

### E1 — Calibration (raw OvR sigmoid probabilities)

| Metric | IN (GoEmotions) | OUT (journaling synth) | Delta |
|---|---|---|---|
| macro-ECE (10 bins) | 0.0902 | 0.1196 | +0.0294 (+33%) |
| micro-ECE | 0.1137 | 0.1170 | +0.0033 |
| mean(conf) - mean(acc) | +0.0902 (overconfident) | +0.1180 (overconfident) | +0.031 |
| micro-Brier | 0.0510 | 0.0724 | +0.021 (+41%) |
| macro-Brier | 0.0510 | 0.0724 | +0.021 |

Interpretation: probabilities are **already overconfident in-domain** (ECE ~0.09
well above the ~0.02 "well-calibrated" reference) and become **more
overconfident out-of-domain** (ECE ~0.12, Brier +41%). This supports H1.

### E2 — Discriminative shift

| Metric | IN | OUT | Delta |
|---|---|---|---|
| micro-F1 | 0.464 | 0.270 | -42% |
| macro-F1 | 0.405 | 0.345 | -15% |
| samples-F1 | 0.495 | 0.299 | -40% |
| hamming acc | 0.178 | 0.092 | -48% |

Largest per-class drops (macro-F1, in->out):
approval 0.46->0.04, relief 0.40->0.14, annoyance 0.47->0.14, sadness
0.56->0.16, joy 0.61->0.25, grief 0.52->0.18, optimism 0.60->0.47, fear
0.69->0.36. Preserved: gratitude 0.92->0.48, amusement 0.83->0.72, remorse
0.71->0.78, surprise 0.58->0.69 (high-arousal/emblematic emotions survive;
subtle/clinical-emotion words degrade).

This supports H2: micro/samples-F1 drop ~40%, concentrated in low-arousal /
clinical-emotion classes (sadness, grief, relief, approval).

### E3 — Propagation into the risk engine & discrepancy policy

Risk trigger rate (= risk_score >= auto_trigger_threshold 8):

| Condition | IN (2000 sampled) | OUT (1730 all) |
|---|---|---|
| raw model probs | 1.40% | 2.77% (= 2.0x) |
| isotonic-calibrated reference | 0.90% | 2.83% |
| decision-flip rate (raw vs calibrated) | 0.90% | 0.87% |

Interpretation: the risk engine's trigger rate roughly **doubles** on
journaling-style text (1.4% -> 2.8%). Calibration shifts a small number of
individual decisions in-domain (significantly, see Phase 9), but the dominant
effect is **domain shift on the label/score distribution**, not raw probability
calibration. Supports H3 (decisions move with the model distribution).

Discrepancy policy (rule-based `discrepancy._detect`, high-stress bio
bpm=118/hrv=22):
- Negative OOD texts: 0/131 flagged (negative + high-stress is NOT a
  discrepancy under the shipped rules — correct per design).
- Neutral GoEmotions samples: 1,711/1,787 (95.7%) flagged (neutral + high-stress
  IS a discrepancy by design).
This confirms the discrepancy layer is deterministic and its "accuracy" is a
policy property, NOT a learned result — exactly as the Phase 1 audit concluded.
No further claim is made on it.

### E4 — Selective prediction (confidence abstention)

| Threshold tau | IN coverage | IN selective err | OUT coverage | OUT selective err |
|---|---|---|---|---|
| 0.00 (always-detect) | 100% | 0.822 | 100% | 0.908 |
| 0.50 | 99% | 0.820 | 99.5% | 0.905 |
| 0.70 | 89.7% | 0.817 | 87.7% | 0.888 |
| 0.85 | 60.7% | 0.800 | 64.8% | 0.865 |
| 0.90 | 47.3% | 0.787 | 56.1% | 0.840 |
| 0.95 | 32.3% | 0.763 | 43.0% | 0.799 |
| 0.98 | 21.2% | 0.674 | 26.5% | 0.802 |

Interpretation (NEGATIVE RESULT — important and honest): max-probability
confidence abstention barely rescues reliability in-domain (error drops only
0.82->0.67 at 21% coverage) and **fails out-of-domain** (0.91->0.80 at 26%
coverage). The classifier's confidence is *not* a reliable selector under the
shift we measured — consistent with the overconfidence finding (E1) and with
the literature (selective prediction requires calibrated confidence; ours is
miscalibrated). This REFUTES the naive mitigation H4(as-stated): a simple
confidence threshold does not preserve recall while cutting FPR. It motivates
calibration-then-select (Phase 10 recommendations section).

---

## 2. Statistical analysis (Phase 9)

Computed by `backend/benchmarks/run_phase9_stats.py` (1,000 paired
bootstraps, seed 42; McNemar via exact binomial on discordant pairs).

- **Bootstrap 95% CIs:**

| Quantity | Estimate | 95% CI |
|---|---|---|
| ECE_IN | 0.0902 | [0.0894, 0.0911] |
| ECE_OUT | 0.1200 | [0.1184, 0.1216] |
| micro-F1_IN | 0.4644 | [0.4558, 0.4725] |
| micro-F1_OUT | 0.2703 | [0.2566, 0.2841] |
| Brier_IN | 0.0510 | [0.0503, 0.0518] |
| Brier_OUT | 0.0724 | [0.0708, 0.0740] |

  CIs for the IN vs OUT deltas do not overlap -> differences are significant
  (delta-ECE [0.0273, 0.0323], delta-micro-F1 [0.1717, 0.2158], both exclude 0).

- **McNemar test (raw vs calibrated reference decisions, discordant pairs):**
  - IN (b=raw-off/cal-on 4, c=raw-on/cal-off 14): p = 0.031 -> SIGNIFICANT at
    5%; calibration removes more triggers in-domain than it adds.
  - OUT (b=8, c=7): p = 1.00 -> NOT significant. Under shift the calibrated
    reference barely re-orders the trigger decision.
  Conclusion: calibration has a small, measurable effect on decisions
  in-domain but is swamped by the distribution-shift effect out-of-domain.

## 3. Claim audit of hypotheses

| Hyp | Status | Evidence |
|---|---|---|
| H1 calibration degrades under shift | SUPPORTED | ECE 0.090->0.120, Brier 0.051->0.072 |
| H2 shift hurts discriminative perf, esp. low-arousal | SUPPORTED | micro-F1 0.464->0.270; sadness/grief/relief drops |
| H3 miscalibration/decision propagation | SUPPORTED (weak calibration effect) | trigger rate 1.4%->2.8% (shift-driven); McNemar IN p=0.031, OUT p=1.00 |
| H4 abstention preserves recall & cuts FPR | REFUTED | selective error barely improves; out-of-domain worst |

## 4. Reproducibility
- Scripts: `backend/benchmarks/run_research_experiments.py`,
  `backend/benchmarks/run_phase9_stats.py` (statistics),
  `backend/benchmarks/run_clean_in_domain.py` (identifies leak-free subset; now
  informational since the model is leak-free).
- Data: GoEmotions (HF, `simplified`), product templates; all anonymous.
- Outputs: `research_results.json`, `research_calibration.csv`,
  `research_clean_in.csv`.
- Model artifact: `emotion_model.pkl` (MD5 9a8d157c...), registry documents
  training split.

## 5. What the paper must say (honesty block)
- OOD domain is synthetic/templated; NOT clinical; no human-subjects claims.
- The discrepancy engine is rule-based; its "results" are policy consistency,
  not learned performance.
- Selective prediction NEGATIVE result is a finding, not a failure of the
  method alone — it strengthens the calibration recommendation.
- Leak fix documented as F5; old 0.465 figures superseded by
  0.4642/0.4047/0.4947 (official test, no leakage).