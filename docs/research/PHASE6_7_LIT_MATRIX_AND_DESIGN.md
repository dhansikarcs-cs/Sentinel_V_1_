# Phase 6 & 7 — Literature Matrix and Full Experimental Design

Status: COMPLETE (design locked)
Predecessors: `PHASE5_QUESTION_SPEC.md`, `PHASE3_4_GAPS_AND_QUESTIONS.md`

---

## 1. Literature Matrix (anchored, 2020-2026)

| # | Reference (short) | Domain | Key finding used | How it supports this study |
|---|---|---|---|---|
| L1 | Demszky et al., 2020 "GoEmotions: A Dataset of Fine-Grained Emotions" (arXiv:2005.00547) | Text emotion | 58k Reddit comments, 28 labels, BERT-base micro-F1 0.46/macro 0.43; annotation subjectivity kappa 0.33-0.44 | Defines the *in-domain* reference; gives us the BERT comparator numbers; documents label subjectivity |
| L2 | Alvarez-Gonzalez et al., 2021 (TF-IDF+LR on GoEmotions) | Text emotion, classical ML | TF-IDF+LR reaches ~0.53 micro-F1 | Validates Sentinel's architecture choice (0.464 is in-family); anchors the classical baseline |
| L3 | Herath, 2025 (IJCA 187/63) "Managing Distribution Shift in Speech Emotion Recognition" | SER, classical models | Cross-domain accuracy collapse (0.914→0.266-0.311); confidence filtering recovers reliability on a subset | Direct template for our E4 selective-prediction; shows classical models DO degrade under shift |
| L4 | arXiv 2503.22712 (2025) "Risk-Calibrated Affective Speech Recognition via Conformal" | Affective computing, uncertainty | Raw confidence unreliable under shift; uncertainty must be quantised when feeding downstream mental-health decisions | Justifies studying calibration specifically; supports conformal/selective framing as mitigation |
| L5 | Ovadia et al., 2019 (NeurIPS) "Can you trust your model's uncertainty?" | Calibration under shift | Calibration degrades under distribution shift; simple calibration fails OOD | Core theoretical anchor for "shift → miscalibration" |
| L6 | Guo et al., 2017 (ICML) "On Calibration of Modern Neural Networks" | Calibration | Deep nets overconfident; ECE as standard; temperature scaling | Provides ECE methodology; contrasts classical LR (ours) vs DNN behaviour |
| L7 | Niculescu-Mizil & Caruana, 2005 (ICML) "Predicting Good Probabilities" | Calibration, classical ML | LR probabilities are *partially calibrated* (isotonic/Platt improve them) | Baseline expectation: LR better calibrated than DNN but still improvable |
| L8 | Zadrozny & Elkan, 2002 (ICML) | Calibration, OvR | One-vs-rest OvR requires per-class calibration; each OvR binary prob needs separate treatment | Exactly our multi-label OvR structure; motivates per-class ECE analysis |
| L9 | Grünwald et al. metricgate/statstest overviews (2026) + sklearn docs | Calibration metrics | ECE/MCE/Brier definitions; ECE>0.10 "red flag"; report Brier alongside ECE (proper score) | Locks our metric suite & reporting template |
| L10 | Rashid et al. / selective-prediction survey threads (Geifman & El-Yaniv 2017; Chow 1970; arXiv 2505.15008 2025) | Selective prediction | Coverage/risk trade-off; confidence threshold selector g(x)=1[s(x)>tau]; abstention for reliability | Formalises E4 (coverage vs risk curves, MC for flips) |
| L11 | Sci. Rep. 2024 (Rainio et al.) / MLmetrics reviews | ML statistics | Metrics choice for imbalanced multi-label; proper scoring rules | Multi-label ECE practices & reporting |
| L12 | Multiple mental-health NLP works: depression-detection on social media, quantum/ensemble emo (PMC11730989, Sci.Rep 2020, CDC/LLM crisis-transfer) | Mental-health NLP | Systems typically use LLM/transformers; classical lightweight baseline rarely characterised for *calibration*, not just accuracy | Distinguishes our contribution (calibration-of-lightweight, not another accuracy report) |
| L13 | WHO / RDoC continuum framing (Sci. Dir. review, 2024) | Mental-health | Risk is on a continuum, subjective-emotion report is a key channel | Frames why emotion probability (not just binary label) is clinically meaningful |

### Gap the matrix confirms
The literature contains (a) calibration-of-classical-ML, (b) shift-in-SER, and
(c) selective prediction separately — but **no** study that measures
*lightweight text-emotion classifier probability calibration* AND *its
propagation into rule-based mental-health risk/discrepancy decisions* with
*selective prediction as mitigation*. That intersection is our contribution.

---

## 2. Experimental Design (locked)

### 2.0 Environment & reproducibility
- Location: `backend/benchmarks/` (CSV logbook + python script per experiment).
- Fixed seed 42, fixed shipped model `emotion_model.pkl`, fixed thresholds as in code.
- All experiments via the real public API (`EmotionClassifier.predict_proba`,
  `risk_engine.assess_risk_with_explainability`, `discrepancy._detect`).

### 2.1 Data sets (fully specified, honest)
- **D_IN**: GoEmotions official test split (5,427) + validation (5,426) = 10,853.
  Multi-hot labels, 28 cols. In-domain = same genre the model saw in training.
- **D_CALIB** (for calibrated-reference): GoEmotions train split (43,410),
  used ONLY to fit an isotonic calibrator per class. Its label source is real.
- **D_OUT**: product's own mental-health journaling templates
  (`crisis_emotion_templates` for fear/sadness/grief/anger/admiration/amusement +
  the `neutral` set in `emotion_classifier.py`), each with a known single
  emotion label. These sentences are the *product's* authored content, disclosed
  as synthetic and NOT clinical. We treat this as an OOD proxy whose domain
  difference (structured journal-style first-person sentences vs Reddit comment
  fragments) is real and measurable.

### 2.2 E1 — Calibration (in vs out)
- Per-class binary ECE (10 uniform bins) on raw OvR sigmoid output, aggregated
  weighted by class prevalence; also macro-average ECE.
- Brier score per class and aggregated (micro and macro), on D_IN and D_OUT.
- Over/under-confidence split (mean(conf) - mean(acc)) per domain.
- Reliability table (bins: count, conf, acc, gap) exported to CSV.
- Expectation from L5/L6: ECE_OUT > ECE_IN, driven by high-risk emotions.

### 2.3 E2 — Shift (discriminative performance)
- micro-F1, macro-F1, samples-F1, precision, recall (threshold 0.5) on D_IN and D_OUT.
- Per-class precision/recall/F1; largest-drop analysis (delta macro-F1 per class).
- Confusion/drift summary: which classes degrade; do low-arousal (sadness,
  nervousness, neutral) degrade more (per L3).

### 2.4 E3 — Propagation into risk & discrepancy decisions
- Feed model probabilities to `assess_risk_with_explainability` and
  `discrepancy._detect` for every D_IN and D_OUT sample.
- Measure: risk-score distribution, % crossing `CRISIS_POLICY.auto_trigger_threshold`,
  % discrepancy-flagged, as a function of domain.
- **Calibrated-counterfactual**: fit per-class isotonic regression on D_CALIB
  probabilities → remap probabilities → re-run risk & discrepancy → count
  **decision flips** vs the raw-probability pipeline. This isolates the effect
  of miscalibration from the effect of shift itself.
- McNemar test on the flip matrix to quantify whether differences are
  statistically significant.

### 2.5 E4 — Selective prediction (abstention)
- Confidence score s(x) = max over class of OvR sigmoid (the "confidence" of the
  top label).
- Sweep tau in [0,1] on D_IN and D_OUT; report coverage = P(g=1), selective risk
  = error rate on accepted, precision/recall on accepted, FPR/TPR at the
  crisis-risk & discrepancy decisions.
- Compare vs always-detect (current product policy, tau=0).
- Identify tau* = min tau achieving >= recall of always-detect at significantly
  lower FPR; report coverage penalty.

### 2.6 Statistics
- ECE/MCE/Brier (point estimates + Wilson 95% CI via bootstrap 1,000 resamples).
- McNemar's test (exact binomial) for pairwise decision-flip comparisons.
- Paired bootstrap difference tests for ECE_IN vs ECE_OUT.

### 2.7 Ethics & honesty block (also in manuscript)
- Synthetic OOD text only; no real human journal data; no IRB-eligible activity.
- All outcomes presented as algorithmic/engineering, never clinical.
- Crisis timings (30s/60s) and discrepancy thresholds = configuration, not evidence.

### 2.8 Figure/table deliverables
- F1 reliability diagrams (in vs out, top-4 risk classes + aggregate).
- F2 per-class delta-F1 (shift bar chart).
- F3 risk-score distribution (in vs out) + decision-flip Sankey/table.
- F4 precision-recall vs coverage (selective prediction).
- T1 model card + full metric table (both domains).
- T2 reliability table; T3 decision-flip matrix.