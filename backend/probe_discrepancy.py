"""Probe the discrepancy engine (_detect) for classification bugs.

Each case declares the EXPECTED sentiment + discrepancy for that (text,bpm,hrv).

Run:  python probe_discrepancy.py
"""

import sys

sys.path.insert(0, ".")

from app.api.discrepancy import _detect  # noqa: E402

# (label, text, bpm, hrv, expected_sentiment, expected_discrepancy)
CASES = [
    # Depressive words from the seeded hrvdemo timeline
    ("worthless", "feeling worthless and guilty about everything", 72, 40, "negative", False),
    ("heaviness", "Woke up with that familiar heaviness again. Didn't sleep well.", 72, 40, "negative", False),
    ("cried hours", "Cried for hours without really knowing why.", 72, 40, "negative", False),
    ("anhedonia", "Nothing brings me joy anymore.", 72, 40, "negative", False),
    ("burden", "Felt like a burden to everyone around me.", 72, 40, "negative", False),
    ("ruminating", "Woke up at 4am replaying old mistakes over and over. Ruminating again.", 72, 40, "negative", False),
    ("can't get out", "Couldn't get out of bed until noon. Canceled plans again.", 72, 40, "negative", False),
    (
        "don't trust good",
        "I don't trust the good moments. Waiting for the other shoe to drop.",
        72,
        40,
        "negative",
        False,
    ),
    # "joy ... anymore" false-positive guard
    ("joy negated by anymore", "Nothing brings me joy anymore", 72, 40, "negative", False),
    ("just joy", "I feel lots of joy today", 72, 60, "positive", False),
    # Negation polarity (Bug A): negated positive -> negative
    ("not happy", "I am not happy today", 72, 40, "negative", False),
    ("not feeling great", "I am not feeling great at all", 72, 40, "negative", False),
    ("not terrible (double-neg -> neutral)", "I am not feeling terrible today", 72, 60, "neutral", False),
    # Idiom: can't stop X should not flip X
    ("can't stop laughing", "I can't stop laughing", 72, 40, "positive", False),
    ("can't stop crying", "I can't stop crying", 72, 40, "negative", False),
    ("crying idiom w/ high stress", "I can't stop crying", 120, 20, "negative", False),
    # Cross-window negation should NOT bleed
    ("not ... better spread", "not feeling great today but actually today was better", 60, 30, "neutral", False),
    # Substring handling: 'dying' should not fire 'die'
    ("substring handling", "I was dying my hair", 72, 40, "neutral", False),
    # High-stress discrepancy directions
    ("positive + high stress", "Everything is amazing, perfect, wonderful", 110, 20, "positive", True),
    ("neutral + high stress", "The weather changed today", 110, 20, "neutral", True),
    # Discrepancy rule combos
    ("neg + lowstress", "I am hopeless and alone", 60, 60, "negative", True),
    ("pos + highstress", "I am so happy and great", 120, 20, "positive", True),
    ("neutral + highstress", "I walked to the store today", 120, 20, "neutral", True),
    # Controls that must NOT discrepancy
    ("control neg+highstress", "I am hopeless and alone", 120, 20, "negative", False),
    ("control pos+lowstress", "I am so happy and great", 60, 60, "positive", False),
    ("control neutral+moderate", "I walked to the store today", 72, 40, "neutral", False),
    # Multi-word phrases
    ("falling apart", "Everything is falling apart", 140, 11, "negative", False),
    ("sleep forever", "I just want to sleep forever", 129, 17, "negative", False),
    ("nothing anymore phrase", "Nothing makes sense anymore", 138, 12, "negative", False),
]

fails = 0
for label, text, bpm, hrv, exp_sent, exp_disc in CASES:
    disc, sentiment, bio, _ = _detect(text, bpm, hrv)
    ok = sentiment == exp_sent and disc == exp_disc
    if not ok:
        fails += 1
        status = "FAIL"
    else:
        status = "PASS"
    out = f"[{status}] {label:36s} -> sent={sentiment:8s} bio={bio:12s} disc={disc}"
    if not ok:
        out += f"  (expected sent={exp_sent:8s} disc={exp_disc})"
    print(out)

print(f"\n{len(CASES)} cases, {len(CASES) - fails} passed, {fails} failed")
sys.exit(1 if fails else 0)
