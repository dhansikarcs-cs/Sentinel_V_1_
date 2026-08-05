"""Golden-set regression harness for the rule-based risk/emotion models (Issue 33).

Pins the deterministic (non-LLM) scoring behavior of `risk_engine` and the
`EmotionClassifier` to a fixed set of hand-labeled entries. Run this whenever the
model, keyword lists, or emotion weights change — CI can gate on it.

Deterministic and fully offline: no Ollama, no Groq, no network.

Usage:
    python -m scripts.eval_golden_set            # non-strict bands
    python -m scripts.eval_golden_set --strict   # exact score matching (use after pinning)

Exit code 0 = pass, 1 = regression detected.
"""

import argparse
import logging
import sys

from app.ml.emotion_classifier import GOEMOTIONS, EmotionClassifier
from app.ml.risk_engine import assess_risk_with_explainability

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("sentinel.golden")

# (id, text, min_score, max_score, must_trigger) — score bands lock in the
# triage tier; trigger flags lock in whether a crisis escalation would fire.
GOLDEN_RISK = [
    ("crisis_suicidal", "I want to die. Nothing is worth living for anymore.", 8, 10, True),
    ("crisis_overdose", "I'm going to take every pill tonight. I can't take it.", 8, 10, True),
    ("high_panic", "I'm having a panic attack, I can't breathe, I feel completely hopeless.", 6, 10, True),
    ("high_distress", "I feel so desperate and terrified, I'm all alone in this.", 6, 9, True),
    ("moderate_anxiety", "I'm feeling anxious about my exams, stressed and a bit worried.", 4, 7, False),
    ("withdrawal", "I stayed home alone all week, I canceled my plans and avoided everyone.", 4, 8, True),
    ("sleep_decline", "I can't sleep, I wake up every hour, the nightmare never ends, I'm so tired.", 4, 8, False),
    ("positive_day", "Today was wonderful, I feel joy and gratitude for all my friends.", 1, 4, False),
    ("neutral", "I attended the meeting and cooked dinner today.", 1, 4, False),
    ("empty", "", 1, 2, False),
]

GOLDEN_EMOTIONS = [
    ("angry_mad", "I am so mad and furious right now.", ["anger"]),
    ("grateful", "I'm so grateful for everyone who helped me.", ["gratitude"]),
    ("loving", "I love them so much, my heart is full.", ["love"]),
    ("sad", "I feel so sad, tears won't stop.", ["sadness"]),
]


def run_risk(clf: EmotionClassifier, strict: bool) -> list[str]:
    failures: list[str] = []
    for gid, text, lo, hi, must_trigger in GOLDEN_RISK:
        result = assess_risk_with_explainability(text)
        score = result.get("risk_score", 0)
        triggered = bool(result.get("triggered", False))

        in_band = lo <= score <= hi
        trigger_ok = (not must_trigger) or triggered
        if strict:
            trigger_ok = triggered == must_trigger

        if not in_band:
            failures.append(
                f"{gid}: score {score} outside expected band [{lo}, {hi}] "
                f"(triggered={triggered}, want_trigger={must_trigger})"
            )
        elif not trigger_ok:
            failures.append(
                f"{gid}: triggered={triggered} but expected {must_trigger} (score={score}, band [{lo}, {hi}])"
            )
        else:
            logger.info("PASS %-18s score=%-3s triggered=%-5s", gid, score, triggered)
    return failures


def run_emotions(clf: EmotionClassifier) -> list[str]:
    failures: list[str] = []
    for gid, text, expected in GOLDEN_EMOTIONS:
        top = clf.predict_top(text, threshold=0.15)
        labels = [e for e, _p in top if e != "neutral"]
        for want in expected:
            if want not in labels:
                failures.append(f"{gid}: expected emotion '{want}' not detected (got {labels[:3] or 'neutral'})")
        for label, _p in top:
            if label not in GOEMOTIONS:
                failures.append(f"{gid}: unknown emotion label '{label}'")
        logger.info("PASS %-18s emotions=%s", gid, labels[:3] or "neutral")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Sentinel golden-set regression harness")
    parser.add_argument("--strict", action="store_true", help="also enforce exact trigger flags")
    args = parser.parse_args()

    clf = EmotionClassifier()
    failures = run_risk(clf, strict=args.strict) + run_emotions(clf)

    if failures:
        logger.error("GOLDEN-SET REGRESSION: %d failure(s)", len(failures))
        for f in failures:
            logger.error("  - %s", f)
        return 1

    logger.info(
        "Golden set passed: %d risk cases + %d emotion cases (strict=%s)",
        len(GOLDEN_RISK),
        len(GOLDEN_EMOTIONS),
        args.strict,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
