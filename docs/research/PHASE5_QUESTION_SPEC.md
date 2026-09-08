# Phase 5 — Formal Research Question Specification

Status: COMPLETE
Predecessors: `PHASE1_REPO_AUDIT.md`, `PHASE3_4_GAPS_AND_QUESTIONS.md`

---

## 1. Selected research question

> **RQ (primary):** Are the raw one-vs-rest sigmoid probabilities emitted by a
> lightweight (TF-IDF + Logistic Regression) multi-label emotion classifier —
> trained on social-media comments (GoEmotions) — calibrated, both in-domain and
> under a mental-health-journaling-style domain shift; and does any
> miscalibration propagate into the product's deterministic risk-tier and
> discrepancy decisions?

And, as the actionable arm:

> **RQ-appl:** Does confidence-based selective prediction (thresholding emotion
> predictions) reduce false crisis-tier / discrepancy flags without sacrificing
> true positives, compared to the current always-detect policy?

## 2. Why this question (justification)

- It targets the **only non-circular, learned component** in the system
  (emotion classifier), so its conclusions are not an artifact of authored rules.
- It is **measurable with existing data**: real GoEmotions (in-domain reference)
  and the product's own templated mental-health journaling sentences
  (out-of-domain probe, disclosed as synthetic).
- It has **direct product relevance**: Sentinel's risk engine and discrepancy
  detector consume these probabilities as inputs; small probability shifts at
  decision thresholds matter for a crisis-escalation product.
- It fills **G1/G2/G3** from the gap analysis; no located work characterises
  *text* emotion-classifier calibration/shift in a *mental-health* deployment
  with a lightweight classical model (prior work is largely speech-dominant).

## 3. Variables

### Independent variable (IV)
- **Text domain**: [IN] the official held-out GoEmotions *test* split (the
  training-distribution surrogate, no leakage — see F5) vs [OUT] synthetic
  mental-health journaling sentences compiled from Sentinel's own templates.

### Dependent variables (DVs)
1. **Calibration**: Expected Calibration Error (ECE, 10-bins), Brier score
   (multi-label), reliability diagrams, per-class confidence analysis.
2. **Discriminative performance**: micro-F1, macro-F1, samples-F1, precision,
   recall on each domain.
3. **Decision propagation**: rate of risk-tier changes and discrepancy-flag
   flips when using model probabilities vs a hypothetical perfectly-calibrated
   reference (empirical corrections).
4. **Selective-prediction trade-off**: precision/recall and #flags vs confidence
   threshold tau, including coverage at fixed recall floor.

### Controlled
- Single shipped model (`emotion_model.pkl`, MD5 = real-trained model).
- Fixed TF-IDF vectoriser (10k features, ngram 1-3, sublinear).
- Fixed rule thresholds in `risk_engine.py` and `discrepancy.py`.
- Fixed random seed 42 for the original split (documented, not re-run).

## 4. Hypotheses

- **H1 (calibration):** The emotion classifier's probabilities are poorly
  calibrated out-of-domain: ECE(OUT) > ECE(IN), with overconfidence on negative
  (high-risk) emotions in the journaling domain.
- **H2 (shift):** Discriminative performance degrades under shift:
  micro-F1(OUT) < micro-F1(IN), with the largest drop in low-arousal / subtle
  emotions.
- **H3 (propagation):** Miscalibration measurably moves risk-tier and
  discrepancy decisions near their thresholds (decision-flip rate > 0 and
  concentrated at borderline scores).
- **H4 (mitigation):** There exists a confidence threshold tau such that
  selective prediction reduces false flags while preserving >= recall of the
  always-detect policy (statistical comparison via McNemar).

### Null hypotheses
- **H0_1:** ECE(OUT) <= ECE(IN) (no calibration degradation).
- **H0_2:** micro-F1(OUT) >= micro-F1(IN) (no performance drop).
- **H0_3:** decision-flip rate = 0 under a calibrated-reference remapping.
- **H0_4:** no tau improves FPR without reducing TPR (no benefit of abstention).

## 5. Baselines / comparators

| Condition | Purpose |
|---|---|
| In-domain GoEmotions (official test, no leakage — see F5 audit) | reference floor (measured: micro-F1 0.4642, macro-F1 0.4047, samples-F1 0.4947) |
| Published BERT-base GoEmotions (micro-F1 0.46 / macro-F1 0.43, Demszky 2020) | literature comparator for realism check |
| Perfectly calibrated reference (isotonic remap in-domain) | decision-propagation counterfactual |
| Always-detect policy (current product) | selective-prediction baseline |
| Random/chance calibration (ECE where confidence != frequency) | calibration sanity check |

## 6. Experiment plan (Phase 8 execution)

- **E1 Calibration (in vs out):** ECE, Brier, reliability curves on GoEmotions
  test split vs synthetic journal set; per-emotion confidence stats.
- **E2 Shift (per-class breakdown):** micro/macro/samples-F1, per-label
  precision/recall on both domains; largest-drop analysis.
- **E3 Propagation:** feed probabilities to `risk_engine.assess_risk_*` and
  `discrepancy._detect`; compare risk-tier distribution in vs out; simulate
  calibrated-reference via isotonic-in-domain remap; record flips.
- **E4 Selective prediction:** sweep tau; report FPR/TPR/coverage; McNemar at
  chosen tau vs always-detect.
- Every experiment prints to stdout AND logs to a CSV in
  `backend/benchmarks/` for reproducibility.

## 7. Explicit NON-claims (written into the paper)

1. **No clinical validity.** Synthetic templated journals are NOT clinical
   data; outcomes are algorithmic, not clinical.
2. **No human-subjects claim.** No IRB scenario; no patient data used or
   implied. (Still include an ethics/limitations paragraph.)
3. **The OOD domain is a proxy**, constructed from the product's own templates,
   not a real corpus; generalisation estimates are upper-bound-optimistic.
4. **Discrepancy detector is rule-based**; its thresholds are engineering
   policy, not clinically derived thresholds. Crisis escalation timings
   (30s/60s) are configuration, not evidence.
5. **Comparison to BERT is literature-anchored, not re-run**, to avoid
   importing unlicensed weights; stated as a caveat.
6. **No hardware claim.** Ring sensors remain simulated; this paper measures
   the "objective channel" only as a *labelled-feature simulation* used inside
   the discrepancy rules, because the rule inputs are fixed constants in
   `discrepancy.py`. Calibration of biometrics is out of scope.
7. **Lightweight = CPU-friendly, not necessarily best**; the study characterises
   a specific architectural trade-off, it does not argue universal superiority.

## 8. Deliverables (Phase 8-10)
- `backend/benchmarks/` runnable experiment script(s) + CSV logbook.
- Tables/figures (reliability curves, per-class F1, decision-flip matrix,
  precision-recall vs tau).
- Master manuscript (Phase 10) + IRIS adaptation (Phase 11).

## 9. Readiness gate (before Phase 6)
- [x] Question fixed.
- [x] Variables/hypotheses fixed.
- [x] Baselines fixed.
- [x] Non-claims written.
- [x] Data sources audited (real GoEmotions + templated synthetic OOD).
- [ ] Environment check: can the experiment script load GoEmotions test split
      locally (network/disk)? — **Phase 6/7 setup will confirm.**