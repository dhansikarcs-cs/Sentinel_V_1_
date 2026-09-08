"""Baseline + regression checker for the discrepancy engine.

Prints per-profile sentiment/bio/discrepancy vs expected, total accuracy,
and returns non-zero exit if accuracy < 80%.

Usage: python check_discrepancy_regression.py [--json]
"""

import sys

sys.path.insert(0, ".")

from app.api.discrepancy import _detect  # noqa: E402
from benchmarks.profiles import DISCREPANCY_PROFILES  # noqa: E402


def main():
    tp = fp = tn = fn = 0
    failures = []
    for p in DISCREPANCY_PROFILES:
        disc, sentiment, bio, _ = _detect(p.journal_text, p.bpm, p.hrv)
        ok = disc == p.expected_discrepancy
        tp += ok and disc
        fp += (not ok) and disc
        tn += ok and (not disc)
        fn += (not ok) and (not disc)
        if not ok:
            failures.append(
                f"P{p.id:02d} {p.category:26s} expected={p.expected_discrepancy!s:5s} "
                f"got={disc!s:5s} sent={sentiment:8s} bio={bio:12s} text={p.journal_text[:45]!r}"
            )

    total = tp + fp + tn + fn
    acc = (tp + tn) / total * 100 if total else 0.0
    prec = tp / (tp + fp) * 100 if (tp + fp) else 0.0
    rec = tp / (tp + fn) * 100 if (tp + fn) else 0.0

    print(f"accuracy={acc:.1f}%  TP={tp} FP={fp} TN={tn} FN={fn}  prec={prec:.0f}% rec={rec:.0f}%  (n={total})")
    for f in failures:
        print("  FAIL " + f)

    return 0 if acc >= 80 else 1


if __name__ == "__main__":
    sys.exit(main())
