"""Discrepancy detection — 50 profiles, logs TP/FP/FN/TN.

IMPORTANT: this uses the SAME detector the server runs on every request
(`app.api.discrepancy._detect`) so the benchmark characterizes the deployed
system, not a divergent local copy. Latency includes the server source of
truth overhead.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.api.discrepancy import _detect
from benchmarks.profiles import DISCREPANCY_PROFILES


def _detect_discrepancy(text: str, bpm: int, hrv: int) -> bool:
    """Call the deployed server detector; return just the boolean."""
    discrepancy, _, _, _ = _detect(text, bpm, hrv)
    return discrepancy


def run_discrepancy_tests(log_func, quick=False):
    profiles = DISCREPANCY_PROFILES[:10] if quick else DISCREPANCY_PROFILES

    tp = fp = tn = fn = 0
    latencies = []

    for p in profiles:
        t0 = time.perf_counter()
        result = _detect_discrepancy(p.journal_text, p.bpm, p.hrv)
        elapsed = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed)

        if result == p.expected_discrepancy:
            if result:
                tp += 1
            else:
                tn += 1
        else:
            if result:
                fp += 1
            else:
                fn += 1

    avg_lat = sum(latencies) / len(latencies)
    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total * 100 if total else 0
    precision = tp / (tp + fp) * 100 if (tp + fp) else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) else 0

    log_func(
        "Discrepancy Detection",
        1,
        "N/A (rule-based)",
        f"{total} profiles",
        avg_lat,
        f"{accuracy:.1f}% acc",
        accuracy >= 80,
        f"TP={tp} FP={fp} TN={tn} FN={fn} Prec={precision:.0f}% Rec={recall:.0f}%",
    )

    # Log 3 random individual profile detections as separate rows
    import random

    for p in random.sample(profiles, min(3, len(profiles))):
        t0 = time.perf_counter()
        result = _detect_discrepancy(p.journal_text, p.bpm, p.hrv)
        lat = (time.perf_counter() - t0) * 1000
        log_func(
            f"Discrepancy #{p.id}",
            1,
            "N/A",
            f"{len(p.journal_text.split())} words",
            lat,
            "N/A",
            result == p.expected_discrepancy,
            f"text='{p.journal_text[:30]}...' bpm={p.bpm} hrv={p.hrv} expected={p.expected_discrepancy} got={result}",
        )

    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "accuracy": accuracy, "avg_latency_ms": avg_lat}
