"""Held-out evaluation: 50 fresh profiles, frozen thresholds, no tuning."""

import os
import sys
import time
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchmarks.test_discrepancy import _detect_discrepancy


@dataclass
class HeldOutProfile:
    id: int
    journal_text: str
    bpm: int
    hrv: int
    expected_discrepancy: bool
    category: str


# 50 NEW profiles — different texts, different biometrics, same detection rules.
# Expected labels computed from the FROZEN engine rules:
#   positive + high_stress(bpm>=110,hrv<=25) → True
#   negative + low_stress(bpm<=80,hrv>=55)   → True
#   negative + moderate                       → True
#   neutral  + high_stress                    → True
#   otherwise                                 → False

HELD_OUT_PROFILES = [
    # === Group A: Positive text + high stress biometrics → EXPECTED TRUE ===
    HeldOutProfile(1, "Today was wonderful, I feel alive and happy", 115, 22, True, "pos+high"),
    HeldOutProfile(2, "I'm so grateful, everything went perfectly", 125, 18, True, "pos+high"),
    HeldOutProfile(3, "Feeling joyful and excited about tomorrow", 112, 24, True, "pos+high"),
    HeldOutProfile(4, "What a beautiful day, I love being alive", 130, 15, True, "pos+high"),
    HeldOutProfile(5, "I'm doing great, better than ever before", 118, 20, True, "pos+high"),
    HeldOutProfile(6, "Life is good and I feel energetic", 122, 17, True, "pos+high"),
    HeldOutProfile(7, "Feeling peaceful and content with everything", 135, 12, True, "pos+high"),
    HeldOutProfile(8, "I'm happy, really happy today", 110, 25, True, "pos+high"),

    # === Group B: Negative text + low stress biometrics → EXPECTED TRUE ===
    HeldOutProfile(9, "I'm struggling with anxiety and can't cope", 75, 60, True, "neg+low"),
    HeldOutProfile(10, "The fear is overwhelming, I feel scared", 70, 65, True, "neg+low"),
    HeldOutProfile(11, "I feel hopeless and alone in this world", 65, 70, True, "neg+low"),
    HeldOutProfile(12, "Panic attacks are getting worse every day", 78, 58, True, "neg+low"),
    HeldOutProfile(13, "I'm terrified of what tomorrow brings", 72, 62, True, "neg+low"),
    HeldOutProfile(14, "Everything is falling apart and I can't breathe", 68, 68, True, "neg+low"),
    HeldOutProfile(15, "I feel terrible and numb inside", 76, 57, True, "neg+low"),
    HeldOutProfile(16, "The darkness is consuming me, I'm drowning", 74, 63, True, "neg+low"),

    # === Group C: Negative text + moderate biometrics → EXPECTED TRUE ===
    HeldOutProfile(17, "I'm anxious and worried about everything", 95, 40, True, "neg+mod"),
    HeldOutProfile(18, "I feel scared and can't stop worrying", 100, 35, True, "neg+mod"),
    HeldOutProfile(19, "The fear won't leave me alone", 85, 45, True, "neg+mod"),
    HeldOutProfile(20, "I'm struggling to keep it together today", 90, 50, True, "neg+mod"),
    HeldOutProfile(21, "I feel hopeless about my recovery", 105, 30, True, "neg+mod"),
    HeldOutProfile(22, "The anxiety is unbearable right now", 88, 48, True, "neg+mod"),
    HeldOutProfile(23, "I'm drowning in my own thoughts", 98, 38, True, "neg+mod"),
    HeldOutProfile(24, "Panic is taking over, I can't escape", 92, 42, True, "neg+mod"),

    # === Group D: Positive text + calm biometrics → EXPECTED FALSE ===
    HeldOutProfile(25, "I feel great and happy today", 72, 65, False, "pos+calm"),
    HeldOutProfile(26, "What a wonderful morning, feeling refreshed", 68, 70, False, "pos+calm"),
    HeldOutProfile(27, "I'm doing well and feeling content", 75, 60, False, "pos+calm"),
    HeldOutProfile(28, "Feeling grateful and optimistic about life", 70, 68, False, "pos+calm"),
    HeldOutProfile(29, "Today was amazing, I feel alive", 73, 63, False, "pos+calm"),
    HeldOutProfile(30, "I love this beautiful weather today", 69, 72, False, "pos+calm"),
    HeldOutProfile(31, "Feeling energetic and full of joy", 71, 66, False, "pos+calm"),
    HeldOutProfile(32, "I'm cured and feeling peaceful", 67, 74, False, "pos+calm"),

    # === Group E: Negative text + high stress biometrics → EXPECTED FALSE ===
    HeldOutProfile(33, "I feel anxious and scared today", 120, 20, False, "neg+high"),
    HeldOutProfile(34, "The fear is overwhelming me completely", 130, 15, False, "neg+high"),
    HeldOutProfile(35, "I'm struggling and feeling hopeless", 115, 22, False, "neg+high"),
    HeldOutProfile(36, "I can't cope with this panic anymore", 125, 18, False, "neg+high"),
    HeldOutProfile(37, "Everything is terrible and I'm scared", 135, 12, False, "neg+high"),
    HeldOutProfile(38, "I feel alone and the darkness is here", 118, 24, False, "neg+high"),
    HeldOutProfile(39, "The anxiety is unbearable and I'm terrified", 140, 10, False, "neg+high"),
    HeldOutProfile(40, "I'm drowning in fear and panic", 128, 16, False, "neg+high"),

    # === Group F: Neutral text + various biometrics ===
    HeldOutProfile(41, "It was a day.", 72, 65, False, "neutral+calm"),
    HeldOutProfile(42, "Nothing special happened today", 100, 40, False, "neutral+mod"),
    HeldOutProfile(43, "I went to school and came home", 70, 68, False, "neutral+calm"),
    HeldOutProfile(44, "The weather was okay today", 115, 22, True, "neutral+high"),
    HeldOutProfile(45, "I ate lunch at noon", 130, 15, True, "neutral+high"),

    # === Group G: Edge cases ===
    HeldOutProfile(46, "", 72, 65, False, "edge-empty"),
    HeldOutProfile(47, "Fine.", 72, 65, False, "edge-minimal+calm"),
    HeldOutProfile(48, "Fine.", 120, 20, True, "edge-minimal+high"),
    HeldOutProfile(49, "I'm doing okay I guess", 90, 45, False, "edge-ambiguous"),
    HeldOutProfile(50, "Today exists", 110, 25, True, "edge-neutral+high"),
]


def run_held_out_evaluation():
    """Run frozen engine on 50 fresh profiles, print results."""
    tp = fp = tn = fn = 0
    latencies = []
    results = []

    for p in HELD_OUT_PROFILES:
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

        results.append({
            "id": p.id,
            "text": p.journal_text[:40],
            "bpm": p.bpm,
            "hrv": p.hrv,
            "expected": p.expected_discrepancy,
            "got": result,
            "correct": result == p.expected_discrepancy,
        })

    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total * 100 if total else 0
    precision = tp / (tp + fp) * 100 if (tp + fp) else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) else 0
    avg_lat = sum(latencies) / len(latencies)

    print(f"=== HELD-OUT EVALUATION (50 fresh profiles, frozen thresholds) ===")
    print(f"Total profiles:  {total}")
    print(f"True Positives:  {tp}")
    print(f"True Negatives:  {tn}")
    print(f"False Positives: {fp}")
    print(f"False Negatives: {fn}")
    print(f"Accuracy:        {accuracy:.1f}%")
    print(f"Precision:       {precision:.1f}%")
    print(f"Recall:          {recall:.1f}%")
    print(f"Avg latency:     {avg_lat:.4f} ms")
    print()

    # Show mismatches
    mismatches = [r for r in results if not r["correct"]]
    if mismatches:
        print(f"=== MISMATCHES ({len(mismatches)}) ===")
        for m in mismatches:
            print(f"  #{m['id']}: expected={m['expected']} got={m['got']} | bpm={m['bpm']} hrv={m['hrv']} | '{m['text']}'")
    else:
        print("=== NO MISMATCHES ===")

    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "accuracy": accuracy, "precision": precision, "recall": recall,
        "avg_latency_ms": avg_lat, "mismatches": mismatches,
    }


if __name__ == "__main__":
    run_held_out_evaluation()
