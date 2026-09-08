"""Sentinel Research Experiments (Phase 8 execution).

RQ: Are the raw one-vs-rest sigmoid probabilities of a lightweight
(TF-IDF + Logistic Regression) multi-label emotion classifier calibrated,
in-domain and under a mental-health journaling domain shift, and does
miscalibration propagate into the product's rule-based risk and discrepancy
decisions? Can confidence-based selective prediction mitigate unreliable
decisions?

Data sources (honest, as per PHASE6/7 design):
  D_IN    : GoEmotions official test + validation splits (real human labels)
  D_CALIB : GoEmotions train split (used only to fit per-class isotonic
            calibrators for the calibrated-reference counterfactual)
  D_OUT   : the product's own synthetic mental-health journaling templates
            (labelled, disclosed; NOT clinical data)

Reproducibility:
  - ship model: backend/app/ml/emotion_model.pkl (md5 == emotion_model_real.joblib)
  - fixed seed 42, fixed policy thresholds from app.ml.crisis_policy
  - output: CSV logbooks here + printed tables
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
)

from app.api.discrepancy import NEGATIVE_SET, _detect
from app.ml.emotion_classifier import GOEMOTIONS, EmotionClassifier
from app.ml.risk_engine import assess_risk_with_explainability

HERE = Path(__file__).parent
N_BINS = 10
BOOTSTRAP_ITERS = 1000
CLS_INDEX = {e: i for i, e in enumerate(GOEMOTIONS)}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _goemotions_split(split: str) -> tuple[list[str], np.ndarray]:
    from datasets import load_dataset  # noqa: PLC0415

    ds = load_dataset("google-research-datasets/go_emotions", "simplified")
    texts, labels = [], []
    for ex in ds[split]:
        lbl = np.zeros(len(GOEMOTIONS), dtype=np.float32)
        for idx in ex["labels"]:
            if idx < len(GOEMOTIONS):
                lbl[idx] = 1.0
        texts.append(ex["text"])
        labels.append(lbl)
    return texts, np.array(labels, dtype=np.float32)


def load_out_domain() -> tuple[list[str], np.ndarray]:
    """Product's own mental-health journaling templates (D_OUT), labelled."""
    from app.ml.emotion_classifier import (  # noqa: PLC0415
        _generate_training_data,
    )

    # _generate_training_data uses real-templated sentences + correct one-hot emotions.
    texts, labels = _generate_training_data()
    return texts, np.array(labels, dtype=np.float32)


# ---------------------------------------------------------------------------
# Batch predict
# ---------------------------------------------------------------------------


def batch_probabilities(clf: EmotionClassifier, texts: list[str]) -> np.ndarray:
    """Return (n, 28) probability matrix using the shipped predict_proba."""
    rows = []
    for t in texts:
        p = clf.predict_proba(t)
        rows.append([p[e] for e in GOEMOTIONS])
    return np.array(rows, dtype=np.float64)


# ---------------------------------------------------------------------------
# Calibration metrics
# ---------------------------------------------------------------------------


def _per_class_ece(y_true: np.ndarray, probs: np.ndarray) -> dict[str, float]:
    """Binary ECE per class (10 equal-width bins), family = macro/micro."""
    eces = {}
    for c in range(len(GOEMOTIONS)):
        y = y_true[:, c]
        if y.sum() == 0:
            continue
        p = probs[:, c]
        bins = np.linspace(0.0, 1.0, N_BINS + 1)
        idx = np.clip(np.digitize(p, bins) - 1, 0, N_BINS - 1)
        gap = 0.0
        for b in range(N_BINS):
            m = idx == b
            if m.sum() == 0:
                continue
            conf = p[m].mean()
            acc = y[m].mean()
            gap += (m.sum() / len(y)) * abs(conf - acc)
        eces[GOEMOTIONS[c]] = float(gap)
    return eces


def aggregate_ece(y_true: np.ndarray, probs: np.ndarray) -> dict[str, float]:
    eces = _per_class_ece(y_true, probs)
    macro = float(np.mean(list(eces.values())))
    # micro = prevalence-weighted
    prev = y_true.mean(axis=0)
    weights = prev / prev.sum()
    micro = float(sum(eces[GOEMOTIONS[c]] * weights[c] for c in range(len(GOEMOTIONS)) if GOEMOTIONS[c] in eces))
    # over/under-confidence
    conf = probs.mean(axis=0)
    acc = y_true.mean(axis=0)
    over = float(np.nanmean(conf - acc))
    return {"macro_ece": macro, "micro_ece": micro, "conf_minus_acc_mean": over}


def aggregate_brier(y_true: np.ndarray, probs: np.ndarray) -> dict[str, float]:
    micro = float(np.mean((probs - y_true) ** 2))
    # macro brier = unweighted mean of per-class brier
    macro = float(np.mean([brier_score_loss(y_true[:, c], probs[:, c]) for c in range(len(GOEMOTIONS))]))
    return {"micro_brier": micro, "macro_brier": macro}


def per_class_table(y_true: np.ndarray, probs: np.ndarray) -> list[dict]:
    rows = []
    for c in range(len(GOEMOTIONS)):
        y = y_true[:, c]
        p = probs[:, c]
        pred = (p >= 0.5).astype(int)
        tp = int(((pred == 1) & (y == 1)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1c = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        acc_mean = p[y == 1].mean() if y.sum() else np.nan
        rows.append(
            {
                "emotion": GOEMOTIONS[c],
                "n_pos": int(y.sum()),
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1c, 4),
                "mean_conf_pos": round(float(acc_mean), 4) if not np.isnan(acc_mean) else None,
            }
        )
    return rows


def discriminative(y_true: np.ndarray, probs: np.ndarray) -> dict[str, float]:
    pred = (probs >= 0.5).astype(int)
    return {
        "micro_f1": float(f1_score(y_true, pred, average="micro", zero_division=0)),
        "macro_f1": float(f1_score(y_true, pred, average="macro", zero_division=0)),
        "samples_f1": float(f1_score(y_true, pred, average="samples", zero_division=0)),
        "hamming_acc": float(accuracy_score(y_true, pred)),
    }


# ---------------------------------------------------------------------------
# Risk + discrepancy propagation
# ---------------------------------------------------------------------------


def risk_decision(probs_row: np.ndarray, text: str) -> dict[str, float]:
    probs = {e: float(probs_row[CLS_INDEX[e]]) for e in GOEMOTIONS}
    res = assess_risk_with_explainability(text, emotion_probs=probs)
    return {
        "risk_score": res["risk_score"],
        "triggered": float(res["triggered"]),
        "emotion_risk_score": res["explainability"]["emotion_risk_score"],
    }


def discrepancy_decision(probs_row: np.ndarray, text: str, bpm: float, hrv: float) -> bool:
    return bool(_detect(text, bpm, hrv)[0])


def risk_vector(probs_rows: np.ndarray, texts: list[str]) -> list[dict]:
    out = []
    for i, t in enumerate(texts):
        pd = {e: float(probs_rows[i, CLS_INDEX[e]]) for e in GOEMOTIONS}
        res = assess_risk_with_explainability(t, emotion_probs=pd)
        out.append({"risk_score": res["risk_score"], "triggered": bool(res["triggered"])})
    return out


def linear_idx_risk(probs_rows: np.ndarray, texts: list[str]) -> list[dict]:
    return risk_vector(probs_rows, texts)


# ---------------------------------------------------------------------------
# Isotonic calibrated-reference counterfactual
# ---------------------------------------------------------------------------


def fit_isotonic(y_calib: np.ndarray, p_calib: np.ndarray, y_test: np.ndarray, p_test: np.ndarray):
    """Per-class isotonic calibrators on calibration split -> remap test probs."""
    remapped = np.zeros_like(p_test)
    for c in range(len(GOEMOTIONS)):
        iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        iso.fit(p_calib[:, c], y_calib[:, c])
        remapped[:, c] = iso.predict(p_test[:, c])
    return remapped


# ---------------------------------------------------------------------------
# Selective prediction
# ---------------------------------------------------------------------------


def selective_analysis(y_true: np.ndarray, probs: np.ndarray, taus: list[float]) -> list[dict]:
    maxconf = probs.max(axis=1)
    pred = (probs >= 0.5).astype(int)
    correct = (pred == y_true).all(axis=1)  # exact-match multi-label
    rows = []
    for tau in taus:
        accept = maxconf >= tau
        n_accept = int(accept.sum())
        coverage = n_accept / len(y_true)
        if n_accept == 0:
            rows.append({"tau": tau, "coverage": 0.0, "selective_accuracy": np.nan})
            continue
        err = 1.0 - correct[accept].mean()
        rows.append({"tau": tau, "coverage": round(coverage, 4), "selective_error": round(float(err), 4)})
    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def load_all(joint: bool = False):
    clf = EmotionClassifier()
    x_in, y_in = _goemotions_split("test")
    x_val, y_val = _goemotions_split("validation")
    x_train, y_train = _goemotions_split("train")
    x_out, y_out = load_out_domain()

    p_in = batch_probabilities(clf, x_in)
    p_val = batch_probabilities(clf, x_val)
    p_cal = batch_probabilities(clf, x_train)
    p_out = batch_probabilities(clf, x_out)

    return {
        "clf": clf,
        "x_in": x_in,
        "y_in": y_in,
        "p_in": p_in,
        "x_val": x_val,
        "y_val": y_val,
        "p_val": p_val,
        "x_cal": x_train,
        "y_cal": y_train,
        "p_cal": p_cal,
        "x_out": x_out,
        "y_out": y_out,
        "p_out": p_out,
    }


def run_all():
    t0 = time.time()
    d = load_all()
    print(f"[data] loaded + predicted in {time.time() - t0:.0f}s")

    results = {"meta": {}, "experiments": {}}
    results["meta"] = {
        "model": "emotion_model.pkl",
        "md5": "9a8d157c6e42706c43b354df6d1025fc",
        "n_in": len(d["x_in"]),
        "n_val": len(d["x_val"]),
        "n_cal": len(d["x_cal"]),
        "n_out": len(d["x_out"]),
    }

    # ---- E1 calibration ----
    ece_in = aggregate_ece(d["y_in"], d["p_in"])
    ece_out = aggregate_ece(d["y_out"], d["p_out"])
    br_in = aggregate_brier(d["y_in"], d["p_in"])
    br_out = aggregate_brier(d["y_out"], d["p_out"])
    results["experiments"]["E1_calibration"] = {"in": ece_in, "out": ece_out, "brier_in": br_in, "brier_out": br_out}
    print("\n=== E1 CALIBRATION ===")
    print("IN :", json.dumps(ece_in, indent=1))
    print("OUT:", json.dumps(ece_out, indent=1))
    print("Brier IN :", json.dumps(br_in, indent=1))
    print("Brier OUT:", json.dumps(br_out, indent=1))

    # ---- E2 shift ----
    disc_in = discriminative(d["y_in"], d["p_in"])
    disc_out = discriminative(d["y_out"], d["p_out"])
    results["experiments"]["E2_shift"] = {"in": disc_in, "out": disc_out}
    print("\n=== E2 SHIFT (discriminative) ===")
    print("IN :", json.dumps(disc_in, indent=1))
    print("OUT:", json.dumps(disc_out, indent=1))

    perm_in = per_class_table(d["y_in"], d["p_in"])
    perm_out = per_class_table(d["y_out"], d["p_out"])
    results["experiments"]["E2_per_class_in"] = perm_in
    results["experiments"]["E2_per_class_out"] = perm_out

    with open(HERE / "research_calibration.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "metric", "value"])
        for dom, ece, br in (("in", ece_in, br_in), ("out", ece_out, br_out)):
            for k, v in {**ece, **br}.items():
                w.writerow([dom, k, v])

    # ---- E3 propagation by substituting model probabilities with the
    # calibrated-reference (isotonic, fit on D_CALIB) ----
    p_calib_ref = fit_isotonic(d["y_cal"], d["p_cal"], d["y_in"], d["p_in"])
    p_calib_ref_out = fit_isotonic(d["y_cal"], d["p_cal"], d["y_out"], d["p_out"])

    risk_raw_in = risk_vector(d["p_in"][:2000], d["x_in"][:2000])
    risk_cal_in = risk_vector(p_calib_ref[:2000], d["x_in"][:2000])
    risk_raw_out = risk_vector(d["p_out"], d["x_out"])
    risk_cal_out = risk_vector(p_calib_ref_out, d["x_out"])

    trigger_raw_in = sum(1 for r in risk_raw_in if r["triggered"])
    trigger_cal_in = sum(1 for r in risk_cal_in if r["triggered"])
    trigger_raw_out = sum(1 for r in risk_raw_out if r["triggered"])
    trigger_cal_out = sum(1 for r in risk_cal_out if r["triggered"])

    flips_in = sum(1 for a, b in zip(risk_raw_in, risk_cal_in, strict=True) if a["triggered"] != b["triggered"])
    flips_out = sum(1 for a, b in zip(risk_raw_out, risk_cal_out, strict=True) if a["triggered"] != b["triggered"])
    # McNemar discordant pairs: b = raw-off/cal-on, c = raw-on/cal-off
    mcnemar_b_in = sum(
        1 for a, b_ in zip(risk_raw_in, risk_cal_in, strict=True) if (not a["triggered"]) and b_["triggered"]
    )
    mcnemar_c_in = sum(
        1 for a, b_ in zip(risk_raw_in, risk_cal_in, strict=True) if a["triggered"] and (not b_["triggered"])
    )
    mcnemar_b_out = sum(
        1 for a, b_ in zip(risk_raw_out, risk_cal_out, strict=True) if (not a["triggered"]) and b_["triggered"]
    )
    mcnemar_c_out = sum(
        1 for a, b_ in zip(risk_raw_out, risk_cal_out, strict=True) if a["triggered"] and (not b_["triggered"])
    )

    results["experiments"]["E3_risk_propagation"] = {
        "n_in_sampled": len(risk_raw_in),
        "trigger_raw_in": trigger_raw_in / len(risk_raw_in),
        "trigger_cal_in": trigger_cal_in / len(risk_raw_in),
        "flip_rate_in": flips_in / len(risk_raw_in),
        "mcnemar_b_in": mcnemar_b_in,
        "mcnemar_c_in": mcnemar_c_in,
        "n_out": len(risk_raw_out),
        "trigger_raw_out": trigger_raw_out / len(risk_raw_out),
        "trigger_cal_out": trigger_cal_out / len(risk_raw_out),
        "flip_rate_out": flips_out / len(risk_raw_out),
        "mcnemar_b_out": mcnemar_b_out,
        "mcnemar_c_out": mcnemar_c_out,
    }
    print("\n=== E3 RISK PROPAGATION (raw vs isotonic-calibrated reference) ===")
    print(
        f"IN : raw={trigger_raw_in / len(risk_raw_in):.4f} "
        f"calib={trigger_cal_in / len(risk_raw_in):.4f} "
        f"flips={flips_in / len(risk_raw_in):.4f}"
    )
    print(
        f"OUT: raw={trigger_raw_out / len(risk_raw_out):.4f} "
        f"calib={trigger_cal_out / len(risk_raw_out):.4f} "
        f"flips={flips_out / len(risk_raw_out):.4f}"
    )

    # E3b: discrepancy behavior on OUT negative/high-stress vs IN neutral high-stress
    neg_out = [(t, y) for t, y in zip(d["x_out"], d["y_out"], strict=True) if any(w in t.lower() for w in NEGATIVE_SET)]
    disc_neg_out = []
    for t, _ in neg_out:
        disc, _, _, _ = _detect(t, bpm=118, hrv=22)  # high-stress bio
        disc_neg_out.append(disc)
    neutral_in = [(t, y) for t, y in zip(d["x_in"], d["y_in"], strict=True) if y[CLS_INDEX["neutral"]] == 1]
    disc_neutral_in = []
    for t, _ in neutral_in[:2000]:
        disc, _, _, _ = _detect(t, bpm=118, hrv=22)
        disc_neutral_in.append(disc)
    results["experiments"]["E3b_discrepancy"] = {
        "n_neg_out": len(disc_neg_out),
        "n_neg_out_flagged": sum(1 for v in disc_neg_out if v),
        "flagged_rate_neg_out": sum(1 for v in disc_neg_out if v) / max(len(disc_neg_out), 1),
        "n_neutral_in_sampled": len(disc_neutral_in),
        "flagged_rate_neutral_in": sum(1 for v in disc_neutral_in if v) / max(len(disc_neutral_in), 1),
    }
    print("\n=== E3b DISCREPANCY (high-stress bio, text sentiment) ===")
    print(f"neg OOD flagged: {sum(1 for v in disc_neg_out if v)}/{len(disc_neg_out)}")
    print(f"neutral IN flagged: {sum(1 for v in disc_neutral_in if v)}/{len(disc_neutral_in)}")

    # ---- E4 selective ----
    taus = [0.0, 0.3, 0.5, 0.7, 0.85, 0.9, 0.95, 0.98]
    sel_in = selective_analysis(d["y_in"], d["p_in"], taus)
    sel_out = selective_analysis(d["y_out"], d["p_out"], taus)
    results["experiments"]["E4_selective_in"] = sel_in
    results["experiments"]["E4_selective_out"] = sel_out
    print("\n=== E4 SELECTIVE PREDICTION ===")
    print("IN :", json.dumps(sel_in, indent=1))
    print("OUT:", json.dumps(sel_out, indent=1))

    with open(HERE / "research_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\n[Saved] research_results.json, research_calibration.csv")


if __name__ == "__main__":
    run_all()
