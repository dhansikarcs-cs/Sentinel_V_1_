"""Clean in-domain reference: evaluate on OFFICIAL GoEmotions test rows that
were NOT leaked into the model's training split.

FLAW DOCUMENTED: train_goemotions.py merges train+validation+test and takes a
random 80/20 split (seed 42), so 4346/5427 official test rows were inside the
training partition. In-domain numbers computed on the full official test set
are therefore optimistic (memorization). This script rebuilds that exact split
and evaluates only the 1081 leak-free test rows, plus re-runs calibration,
risk-propagation and selective-prediction on that clean subset.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmarks.run_research_experiments import (  # noqa: PLC0415
    EmotionClassifier,
    _goemotions_split,
    aggregate_brier,
    aggregate_ece,
    batch_probabilities,
    discriminative,
    risk_vector,
    selective_analysis,
)

HERE = Path(__file__).parent


def main():
    # Load all three splits exactly as train_goemotions does (flat list order).
    x_tr, y_tr = _goemotions_split("train")
    x_va, y_va = _goemotions_split("validation")
    x_te, y_te = _goemotions_split("test")

    all_texts = list(x_tr) + list(x_va) + list(x_te)
    n = len(all_texts)
    idxs = np.arange(n)
    tr_idx, te_idx = train_test_split(idxs, test_size=0.2, random_state=42)
    train_set = {int(i) for i in tr_idx}
    # test split positions (20% holdout used by training script)
    holdout = {int(i) for i in te_idx}

    # Official-test rows that are leak-free (in holdout partition AND from 'test' split)
    test_offset = len(x_tr) + len(x_va)  # official test starts here
    leak_free_idx = [int(i) for i in holdout if i >= test_offset]
    leaked_idx = [int(i) for i in train_set if i >= test_offset]

    print(f"official test rows: {len(x_te)}; leaked into train: {len(leaked_idx)}; leak-free: {len(leak_free_idx)}")

    clf = EmotionClassifier()
    lf_pos = [i - test_offset for i in leak_free_idx]
    x_clean = [x_te[p] for p in lf_pos]
    y_clean = y_te[lf_pos]
    p_clean = batch_probabilities(clf, x_clean)

    print("hamming/micro/macro/samples on LEAK-FREE official test:", json.dumps(discriminative(y_clean, p_clean)))
    ece = aggregate_ece(y_clean, p_clean)
    br = aggregate_brier(y_clean, p_clean)
    print("ECE clean:", json.dumps(ece))
    print("Brier clean:", json.dumps(br))

    # risk propagation on clean subset
    risk_clean = risk_vector(p_clean, x_clean)
    trig = sum(1 for r in risk_clean if r["triggered"])
    print(f"clean trigger rate: {trig}/{len(risk_clean)} = {trig / len(risk_clean):.4f}")

    # selective on clean subset
    taus = [0.0, 0.3, 0.5, 0.7, 0.85, 0.9, 0.95, 0.98]
    sel_clean = selective_analysis(y_clean, p_clean, taus)
    print("selective clean:", json.dumps(sel_clean))

    with open(HERE / "research_clean_in.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        for k, v in {
            **discriminative(y_clean, p_clean),
            **ece,
            **br,
            "clean_trigger_rate": trig / len(risk_clean),
        }.items():
            w.writerow([k, v])
    print("[Saved] research_clean_in.csv")


if __name__ == "__main__":
    main()
