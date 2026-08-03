"""Discrepancy detection — 50 profiles, logs TP/FP/FN/TN."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchmarks.profiles import DISCREPANCY_PROFILES


def _detect_discrepancy(text: str, bpm: int, hrv: int) -> bool:
    """Local deterministic discrepancy detector (mirrors server logic)."""
    text_lower = text.lower().strip()

    positive_words = {
        "great",
        "happy",
        "good",
        "wonderful",
        "amazing",
        "fantastic",
        "energetic",
        "refreshed",
        "joy",
        "love",
        "beautiful",
        "perfect",
        "cured",
        "better",
        "peaceful",
        "content",
        "grateful",
        "optimistic",
    }
    negative_words = {
        "anxious",
        "scared",
        "terrified",
        "panic",
        "fear",
        "afraid",
        "hopeless",
        "die",
        "kill",
        "suicide",
        "disappear",
        "worried",
        "can't",
        "cannot",
        "unbearable",
        "drowning",
        "alone",
        "numb",
        "struggling",
        "darkness",
        "terrible",
        "falling apart",
    }
    negation_prefixes = {
        "not",
        "no",
        "never",
        "don't",
        "dont",
        "doesn't",
        "doesnt",
        "isn't",
        "isnt",
        "wasn't",
        "wasnt",
        "won't",
        "wont",
        "can't",
        "cant",
        "couldn't",
        "couldnt",
        "shouldn't",
        "shouldnt",
        "wouldn't",
        "wouldnt",
        "hardly",
        "barely",
        "neither",
        "nor",
    }

    words = text_lower.split()
    negated = set()
    i = 0
    while i < len(words):
        if words[i] in negation_prefixes and i + 1 < len(words):
            for j in range(i + 1, min(i + 4, len(words))):
                candidate = words[j].rstrip(".,!?;:")
                if candidate in positive_words:
                    negated.add(candidate)
                if candidate in negative_words:
                    negated.add(candidate)
            i += 2
        else:
            i += 1

    effective_pos = positive_words - negated
    effective_neg = negative_words - negated

    has_positive = any(w in text_lower for w in effective_pos)
    has_negative = any(w in text_lower for w in effective_neg)

    if has_positive and not has_negative:
        text_stress = "low"
    elif has_negative and not has_positive:
        text_stress = "high"
    else:
        text_stress = "neutral"

    # Biometric stress
    high_stress = bpm >= 110 and hrv <= 25
    low_stress = bpm <= 80 and hrv >= 55
    moderate = not high_stress and not low_stress

    # Discrepancy = mismatch between text sentiment and biometric state
    if text_stress == "low" and high_stress:
        return True
    if text_stress == "high" and low_stress:
        return True
    if text_stress == "high" and moderate:
        return True  # anxious words + mid biometrics = still a concern
    return text_stress == "neutral" and high_stress  # neutral text but extreme biometrics


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
