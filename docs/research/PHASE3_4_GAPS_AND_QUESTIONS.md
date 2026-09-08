# Phase 3 & 4 — Research-Gap Analysis and Candidate Research Questions

Status: COMPLETE (as of this writing)
Companion: `PHASE1_REPO_AUDIT.md` (artifact inventory + evidence map + flaws F1-F5)

---

## 0. Scope and data-access statement (anonymity / honesty)

This document is written as anonymous research. It contains no patient data, no
identifying names, and no claims about real human subjects. Sentinel's training
data is **GoEmotions** (a public, de-identified Reddit-annotation dataset,
Demszky et al. 2020): 58k comments, 28 emotion labels. The deployment scenario
we study is *synthetic mental-health journaling text* (templated examples in the
product's own code), clearly labelled as such. **Nothing here is clinical
evidence; no experiment in this pipeline involves human participants.**

---

## 1. What is actually researchable in this codebase (evidence floor recap)

From the Phase 1/2 audit, three artifacts form the defensible core:

| Component | Type | Evidence class | Non-circular? |
|---|---|---|---|
| Emotion classifier (`app/ml/emotion_classifier.py` + `emotion_model.pkl`) | TF-IDF(10k) + OneVsRest LogisticRegression (C=2.0, balanced) trained on real GoEmotions official train+val (48,836 samples; leak-free split, see F5) | [IMPLEMENTED + EXPERIMENTALLY TESTED] | **YES** — real human labels; metrics computed on held-out official test (micro-F1 0.464) | 
| Risk engine (`app/ml/risk_engine.py`) | Rule-based (emotion-weight blend + crisis keyword tiers) | [IMPLEMENTED] | No learning; deterministic policy |
| Discrepancy detector (`app/api/discrepancy.py`) | Rule-based (fixed thresholds) | [IMPLEMENTED] | No learning; deterministic policy |

Key nuance verified during Phase 1/2: the shipped model `emotion_model.pkl` is
byte-identical (MD5) to the real-trained `emotion_model_real.joblib`, so the
deployed artifact is genuinely the GoEmotions-trained model. NOTE (Sep 2026,
audit F5): the original registry metrics were computed with a validation-leak
80/20 re-split of the merged splits; after fixing the split to official
train+val / official test, the honest metrics are micro-F1 0.464 / macro-F1
0.405 on the truly held-out official test.
There is no distribution-shift / cross-domain evaluation anywhere in the repo —
this is the open gap (addressed in Phases 6–9).

---

## 2. Phase 3 — Gap analysis from literature

### 2.1 Literature anchors (searched 2026)

1. **GoEmotions benchmark (Demszky et al., 2020)** — BERT-base achieves
   micro-F1 0.46 / macro-F1 0.43 across 28 labels. A classical TF-IDF+LR
   baseline (Alvarez-Gonzalez et al., 2021) reaches ~0.53 micro-F1. Sentinel's
   0.464 micro-F1 (leak-free) is therefore **in the normal range** for this task and model
   family — a credible, unexaggerated baseline, and a genuinely deployable
   lightweight alternative to Transformers on CPU/edge.

2. **Fine-grained emotion detection overview (arXiv 2601.18162, 2026)** —
   documents known difficulties: severe class imbalance, human subjectivity,
   low inter-annotator agreement (kappa ~0.33-0.44 on GoEmotions).

3. **Distribution shift in emotion recognition (IJCA 2025, Herath)** — classical
   models (LR/RF/XGBoost) achieve strong in-domain accuracy but **collapse under
   domain/corpus shift** (e.g. 0.914 -> 0.266-0.311 across corpora/gender).
   *Confidence-based filtering/selective prediction* recovers reliability on a
   trusted subset. Explicitly generalises to "stress-detection systems",
   emphasizing false-positive/false-negative harm in clinical-ish settings.

4. **Risk-calibrated affective recognition via conformal prediction
   (arXiv 2503.22712, 2025)** — uncertainty must be handled explicitly when an
   emotion system feeds a downstream decision (e.g. mental-health monitoring);
   naive softmax/raw sigmoid confidence is NOT reliable under shift.

5. **Calibration metrics & architecture/shift (MDPI 2026)** — post-hoc
   calibration (temperature scaling etc.) materially improves uncertainty
   quality under distribution shift, especially outside the training domain.

6. **Multimodal / discrepancy concept** — widely studied conceptually (objective
   physiology vs subjective report disagreement), but Sentinel's own discrepancy
   layer is rule-based, so any "discrepancy" research must be *framed as a
   policy/engineering contribution*, not a learned result.

### 2.2 Identified gaps (what references do NOT settle)

- **G1**: No published result characterising how a *lightweight* (TF-IDF+LR)
  text emotion model trained on casual social comments behaves on
  **mental-health journaling language** — i.e. whether micro/macro-F1 and
  confidence are degraded by domain shift in *text* (most shift studies are in
  *speech* emotion recognition).
- **G2**: Whether **raw OvR sigmoid probabilities** (exactly what Sentinel feeds
  to its risk/discrepancy rules) are **well-calibrated** in-domain, and what
  happens to calibration **out-of-domain** (mental-health text).
- **G3**: Whether **selective prediction / confidence abstention** (only act on
  high-confidence emotion predictions) improves **crisis-tier / discrepancy
  decision reliability** vs the current always-detect policy — directly useful
  for a crisis-escalation product.
- **G4**: The **emotion-class prior / taxonomy** question: do fine-grained
  GoEmotions categories (28) help or hurt a coarse risk estimate vs a reduced
  (valence-stress) taxonomy — testable entirely within the existing risk engine.

---

## 3. Phase 4 — Candidate research questions (drafted anonymously)

Scoring: novelty (0-3), feasibility within repo (0-3), avoids overclaim (0-3),
IRIS fit (0-3). Max 12. All experiments use ONLY: real GoEmotions test data +
Sentinel's own synthetic templated "journal" text + the shipped models.

### Q1 — Distribution-shift robustness of a lightweight text emotion classifier
**"How does a lightweight (TF-IDF+LR) emotion classifier trained on social
comments (GoEmotions) generalise to mental-health journaling text, and which
emotion classes degrade most?"**
- Method: evaluate shipped `emotion_model.pkl` on (a) held-out GoEmotions (in-domain) vs (b) the product's own mental-health-styled templated sentences (out-of-domain), micro/macro-F1, per-class breakdown, confusion/drift.
- Honestly: out-of-domain label source = templated synthetic sentences with known emotion labels (author-generated, disclosed as synthetic, NOT clinical).
- Novelty 2, Feasibility 3, No-overclaim 2, IRIS 3 → **10/12**.

### Q2 — Are the probabilities that drive a mental-health risk engine calibrated?
**"Is the raw OvR sigmoid probability output of a GoEmotions-trained classifier
calibrated, in-domain and out-of-domain — and does miscalibration bias the
risk-tier / discrepancy decisions it feeds?"**
- Method: reliability curves, ECE, Brier score on in-domain GoEmotions vs out-of-domain templated journals; propagate to risk_engine + discrepancy rules; report decision-flip rate.
- Novelty 2, Feasibility 3, No-overclaim 2, IRIS 3 → **10/12**.

### Q3 — Can confidence-based abstention improve crisis-tier reliability?
**"Does applying a confidence/abstention threshold to emotion predictions reduce
false crisis triggers / discrepancy flags without starving true positives?"
(e.g. selective prediction on the templated journal set and in-distribution
GoEmotions samples re-scored through the product's thresholds.)**
- Method: sweep confidence thresholds; precision-recall at the crisis/auto-trigger and discrepancy decision; compare "always-detect" vs "abstain when unsure".
- Novelty 2, Feasibility 3, No-overclaim 2, IRIS 2 → **9/12**.

### Q4 — Fine-grained vs coarse taxonomy for risk estimation
**"Does collapsing 28 fine-grained emotions to a valence/stress axis change risk
estimation materially vs using the full taxonomy in the product's rule-based
risk engine?"**
- Method: derive coarse axes from the 28 probabilities; recompute risk scores over the synthetic journal set + real GoEmotions neutral/negative strata; measure decision differences.
- Novelty 1, Feasibility 3, No-overclaim 2, IRIS 2 → **8/12**.

### Q5 — Feature sufficiency of Bag-of-Words sentiment for crisis triage
**"For crisis-relevant text, does a transparent word/template-based signal match
a learned multi-emotion model on coarse risk tiering — i.e. is shallow NLP
'good enough' for triage?"**
- Method: compare keyword/lexicon-only risk (rule engine without emotion probs) vs learned-emotion-informed risk on the synthetic journal set; report tier agreement / disagreement and error cases.
- Methodologically honest but arguably under-agentic; overlaps Q1/Q3. Novelty 1, Feasibility 3, No-overclaim 3, IRIS 2 → **9/12**.

### Q6 — Model choice for on-device mental-health emotion monitoring
**"Is a classic TF-IDF+LR emotion model a rational deployment choice (accuracy /
size / latency / calibration trade-off) versus a Transformer for a
smart-ring-and-journal companion?"**
- Method: measure inference latency + model size on-device-ish (local CPU), report GoEmotions micro/macro-F1 vs published BERT (0.46/0.43); discuss calibration gap. Mostly a benchmark/report, partially overlaps "comparative" body of work.
- Novelty 1, Feasibility 3, No-overclaim 3, IRIS 2 → **9/12**.

### Q7 — Discrepancy policy as an engineering artefact
**"An open-spec discrepancy policy that reconciles subjective vs objective channels
in crisis escalation."** — this is real but explicitly rule-based; as a research
paper it becomes a *position/architecture* paper, not empirical. It could
strengthen framing but cannot be the empirical core.
- Novelty 2, Feasibility 3, No-overclaim 1, IRIS 3 → **8/12**.

### Q8 — Selective prediction as a deployable safeguard for crisis triage
-A related but different packaging of Q3: focuses on the *deployment*
  consequence; measure trade-off of coverage vs reliability under a non-negotiable
  recall floor. **Too close to Q3; merge.** Novelty 1 → merged.

---

## 4. Ranked shortlist (for Phase 5 single-question selection)

1. **Q2 (10/12)** — calibration + propagation into decisions. Strongest science,
   most novel, clearest "why it matters", uses the real risk/discrepancy chain.
2. **Q1 (10/12)** — distribution-shift measurement; clean, reproducible, and
   produces the macro/micro F1 evidence table the paper needs.
3. **Q3 (9/12)** — actionable product recommendation; slightly weaker novelty.
4. **Q5 / Q6 (9/12)** — supporting/ablation material for whichever of Q1/Q2 wins.

Recommendation: select **Q2 as primary**, with **Q1 as the distribution-shift
characterisation** it depends on, and **Q3** as the practical application arm —
one coherent experiment programme: *"Calibration and distribution shift in a
lightweight emotion classifier feeding a rule-based mental-health risk /
discrepancy policy, and the case for selective prediction."*

---

## 5. Next step
Phase 5: formalise the selected question with hypothesis, null hypothesis,
independent/dependent variables, intervention/control conditions, baselines,
and explicit non-claims. Then Phase 6 literature matrix, Phase 7 design.