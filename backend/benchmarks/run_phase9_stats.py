"""Phase 9 statistics: bootstrap CIs + McNemar on the research results.

Loads the same datasets/models as run_research_experiments but recomputes the
CIs honestly (no hard-coded numbers).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmarks.run_research_experiments import (  # noqa: PLC0415
    EmotionClassifier,
    _goemotions_split,
    aggregate_brier,
    aggregate_ece,
    batch_probabilities,
    discriminative,
    load_out_domain,
)

RNG = np.random.default_rng(42)
N = 1000


def boot_ci(yy, pp, statfn, n=N, alpha=0.05):
    stats = []
    for _ in range(n):
        idx = RNG.integers(0, len(yy), len(yy))
        stats.append(statfn(yy[idx], pp[idx]))
    lo, hi = np.percentile(stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi), float(np.mean(stats))


def main():
    clf = EmotionClassifier()
    x_in, y_in = _goemotions_split("test")
    x_out, y_out = load_out_domain()
    p_in = batch_probabilities(clf, x_in)
    p_out = batch_probabilities(clf, x_out)

    # ECE IN/OUT (macro)
    ece_in_lo, ece_in_hi, ece_in_mean = boot_ci(y_in, p_in, lambda y, p: aggregate_ece(y, p)["macro_ece"])
    ece_out_lo, ece_out_hi, ece_out_mean = boot_ci(y_out, p_out, lambda y, p: aggregate_ece(y, p)["macro_ece"])
    # micro-F1 IN/OUT
    f1_in_lo, f1_in_hi, f1_in_mean = boot_ci(y_in, p_in, lambda y, p: discriminative(y, p)["micro_f1"])
    f1_out_lo, f1_out_hi, f1_out_mean = boot_ci(y_out, p_out, lambda y, p: discriminative(y, p)["micro_f1"])
    # Brier IN/OUT
    br_in_lo, br_in_hi, br_in_mean = boot_ci(y_in, p_in, lambda y, p: aggregate_brier(y, p)["micro_brier"])
    br_out_lo, br_out_hi, br_out_mean = boot_ci(y_out, p_out, lambda y, p: aggregate_brier(y, p)["micro_brier"])

    print("=== Bootstrap 95% CIs (1,000 resamples, seed 42) ===")
    for name, lo, hi, m in [
        ("ECE_IN", ece_in_lo, ece_in_hi, ece_in_mean),
        ("ECE_OUT", ece_out_lo, ece_out_hi, ece_out_mean),
        ("microF1_IN", f1_in_lo, f1_in_hi, f1_in_mean),
        ("microF1_OUT", f1_out_lo, f1_out_hi, f1_out_mean),
        ("Brier_IN", br_in_lo, br_in_hi, br_in_mean),
        ("Brier_OUT", br_out_lo, br_out_hi, br_out_mean),
    ]:
        print(f"{name:10s} est={m:.4f}  95% CI [{lo:.4f}, {hi:.4f}]")

    # Bootstrap p-value for ECE_IN vs ECE_OUT (paired by size via permutation-ish; use delta CI)
    # delta CI from independent bootstraps:
    dl, dh = ece_out_lo - ece_in_hi, ece_out_hi - ece_in_lo
    print(f"\nDelta ECE(OUT-IN) 95% CI [{dl:.4f}, {dh:.4f}] -> {'significant' if dl > 0 else 'not significant'}")
    print(
        f"Delta microF1(IN-OUT) = {f1_in_mean - f1_out_mean:.4f} "
        f"[{f1_in_lo - f1_out_hi:.4f}, {f1_in_hi - f1_out_lo:.4f}]"
    )

    # McNemar from stored results (discordant pairs b=raw-off/cal-on, c=raw-on/cal-off)
    r = json.loads(Path(__file__).parent.joinpath("research_results.json").read_text(encoding="utf-8"))["experiments"]
    e3 = r["E3_risk_propagation"]
    b_in, c_in = e3["mcnemar_b_in"], e3["mcnemar_c_in"]
    b_out, c_out = e3["mcnemar_b_out"], e3["mcnemar_c_out"]
    p_in_ = binomtest(b_in, b_in + c_in, 0.5, alternative="two-sided").pvalue if (b_in + c_in) else 1.0
    p_out_ = binomtest(b_out, b_out + c_out, 0.5, alternative="two-sided").pvalue if (b_out + c_out) else 1.0
    print(
        f"\nMcNemar(raw vs calibrated reference): IN b={b_in} c={c_in} p={p_in_:.4f}; "
        f"OUT b={b_out} c={c_out} p={p_out_:.4f}"
    )

    # overconfidence t-like via bootstrap of mean(conf)-mean(acc)
    cin = aggregate_ece(y_in, p_in)["conf_minus_acc_mean"]
    cout = aggregate_ece(y_out, p_out)["conf_minus_acc_mean"]
    print(f"overconfidence gap: IN={cin:.4f} OUT={cout:.4f} delta={cout - cin:+.4f}")


if __name__ == "__main__":
    main()
