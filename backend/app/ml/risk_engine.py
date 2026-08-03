import json
from typing import Any

from app.ml.crisis_policy import CRISIS_POLICY

EMOTION_RISK_WEIGHTS: dict[str, float] = {
    "fear": 1.8,
    "sadness": 1.5,
    "anger": 1.3,
    "disgust": 1.2,
    "remorse": 1.2,
    "grief": 1.6,
    "nervousness": 1.4,
    "embarrassment": 1.0,
    "disappointment": 1.1,
    "annoyance": 0.9,
    "confusion": 0.8,
    "disapproval": 0.9,
    "desire": 0.7,
    "surprise": 0.6,
    "curiosity": 0.4,
    "admiration": 0.3,
    "amusement": 0.2,
    "approval": 0.2,
    "caring": 0.3,
    "excitement": 0.3,
    "gratitude": 0.2,
    "joy": 0.1,
    "love": 0.2,
    "optimism": 0.3,
    "pride": 0.3,
    "realization": 0.5,
    "relief": 0.3,
    "neutral": 0.0,
}

CRISIS_KW = [
    "suicide",
    "kill myself",
    "end my life",
    "want to die",
    "not worth living",
    "self-harm",
    "hurt myself",
    "emergency",
    "can't take it",
    "overdose",
]
HIGH_KW = [
    "panic",
    "hopeless",
    "desperate",
    "terrified",
    "screaming",
    "can't breathe",
    "alone",
    "scared",
    "anxiety",
    "afraid",
    "worthless",
    "numb",
]
MEDIUM_KW = ["sad", "worried", "tired", "stress", "overwhelmed", "frustrated", "angry", "upset", "crying", "lost"]
SOCIAL_KW = ["friends", "family", "people", "nobody", "alone", "isolated", "no one", "lonely", "withdrew"]
SLEEP_KW = ["sleep", "insomnia", "tired", "exhausted", "can't sleep", "wake up", "nightmare"]
ACTIVITY_KW = ["nothing", "didn't do", "stay in bed", "no energy", "can't", "avoid", "skipped"]


def _emotion_risk_contribution(emotion_probs: dict[str, float]) -> dict[str, Any]:
    weighted_sum = 0.0
    total_weight = 0.0
    contributions = []
    for emotion, prob in emotion_probs.items():
        weight = EMOTION_RISK_WEIGHTS.get(emotion, 0.5)
        contribution = prob * weight
        weighted_sum += contribution
        total_weight += prob
        if prob > 0.1:
            contributions.append(
                {
                    "emotion": emotion,
                    "probability": prob,
                    "weight": weight,
                    "contribution": round(contribution, 4),
                }
            )
    avg_risk = weighted_sum / total_weight if total_weight > 0 else 0.0
    contributions.sort(key=lambda c: c["contribution"], reverse=True)
    return {
        "emotion_risk_score": round(avg_risk * 10, 2),
        "top_contributors": contributions[:5],
    }


def _keyword_risk_score(text: str) -> dict[str, Any]:
    lower = text.lower()
    crisis = [kw for kw in CRISIS_KW if kw in lower]
    high = [kw for kw in HIGH_KW if kw in lower]
    mod = [kw for kw in MEDIUM_KW if kw in lower]
    social = sum(1 for kw in SOCIAL_KW if kw in lower)
    sleep = sum(1 for kw in SLEEP_KW if kw in lower)
    activity = sum(1 for kw in ACTIVITY_KW if kw in lower)

    score = 1
    if crisis:
        score = 10
    elif high:
        score = 7
    elif mod:
        score = 4
    if social >= 2 or sleep >= 2 or activity >= 2:
        score = max(score, 5)

    return {
        "base_score": score,
        "crisis_keywords": crisis,
        "high_risk_keywords": high[:3],
        "moderate_keywords": mod[:3],
        "social_withdrawal_count": social,
        "sleep_disturbance_count": sleep,
        "activity_decline_count": activity,
    }


def assess_risk_with_explainability(text: str, emotion_probs: dict[str, float] | None = None) -> dict[str, Any]:
    if not text.strip():
        return {"risk_score": 1, "triggered": False, "reasoning": "No content to assess.", "explainability": {}}

    from app.ml.emotion_classifier import classifier

    if emotion_probs is None:
        emotion_probs = classifier.predict_proba(text)

    emotion_analysis = _emotion_risk_contribution(emotion_probs)
    keyword_analysis = _keyword_risk_score(text)

    emotion_component = emotion_analysis["emotion_risk_score"]
    keyword_base = keyword_analysis["base_score"]

    if keyword_base >= 10:
        risk_score = 10
    elif keyword_base >= 7:
        risk_score = min(9, max(5, keyword_base + round(emotion_component * 0.15)))
    elif keyword_base >= 4:
        risk_score = max(3, keyword_base + round(emotion_component * 0.1))
    else:
        risk_score = max(1, round(emotion_component * 0.5))

    risk_score = max(1, min(10, risk_score))

    explain_parts = []
    if emotion_analysis["top_contributors"]:
        top = emotion_analysis["top_contributors"][0]
        explain_parts.append(
            f"Primary emotion signal: {top['emotion']} (P={top['probability']:.2f}, weight={top['weight']:.1f})"
        )
        if len(emotion_analysis["top_contributors"]) > 1:
            explain_parts.append(
                f"Secondary: {emotion_analysis['top_contributors'][1]['emotion']} (P={emotion_analysis['top_contributors'][1]['probability']:.2f})"
            )
    if keyword_analysis["crisis_keywords"]:
        explain_parts.append(f"CRISIS keywords detected: {', '.join(keyword_analysis['crisis_keywords'])}")
    if keyword_analysis["high_risk_keywords"]:
        explain_parts.append(f"High risk: {', '.join(keyword_analysis['high_risk_keywords'])}")
    if keyword_analysis["moderate_keywords"]:
        explain_parts.append(f"Moderate signals: {', '.join(keyword_analysis['moderate_keywords'])}")
    if keyword_analysis["social_withdrawal_count"] >= 2:
        explain_parts.append(f"Social withdrawal ({keyword_analysis['social_withdrawal_count']}x)")
    if keyword_analysis["sleep_disturbance_count"] >= 2:
        explain_parts.append(f"Sleep disturbance ({keyword_analysis['sleep_disturbance_count']}x)")
    if keyword_analysis["activity_decline_count"] >= 2:
        explain_parts.append(f"Activity decline ({keyword_analysis['activity_decline_count']}x)")

    reasoning = f"Score {risk_score}/10. {'; '.join(explain_parts) if explain_parts else 'No significant indicators.'}"

    top_emotions = [c["emotion"] for c in emotion_analysis["top_contributors"] if c["probability"] > 0.15]

    return {
        "risk_score": risk_score,
        "triggered": risk_score >= CRISIS_POLICY.auto_trigger_threshold,
        "reasoning": reasoning,
        "emotions": ", ".join(top_emotions) if top_emotions else "neutral",
        "emotion_probabilities": emotion_probs,
        "explainability": {
            "emotion_risk_score": emotion_analysis["emotion_risk_score"],
            "keyword_base_score": keyword_base,
            "blended_score": risk_score,
            "top_contributors": emotion_analysis["top_contributors"],
            "keyword_signals": {k: v for k, v in keyword_analysis.items() if k != "base_score"},
        },
    }


def assess_risk_with_history(
    text: str, emotion_probs: dict = None, sensor_data: dict = None, recent_texts: list = None
) -> dict:
    """Enhanced risk assessment with temporal trend analysis."""
    base_result = assess_risk_with_explainability(text, emotion_probs)

    if not recent_texts or len(recent_texts) < 3:
        return base_result

    negative_signals = [
        "suicide",
        "kill",
        "die",
        "hopeless",
        "worthless",
        "can't",
        "panic",
        "desperate",
        "numb",
        "empty",
        "alone",
        "hurt",
        "sleep",
        "insomnia",
        "nightmare",
        "crying",
        "lost",
    ]
    positive_signals = [
        "better",
        "hopeful",
        "good",
        "calm",
        "grateful",
        "progress",
        "proud",
        "happy",
        "peaceful",
        "strong",
        "safe",
        "help",
    ]

    recent = recent_texts[-3:]  # Last 3 entries
    older = recent_texts[:-3] if len(recent_texts) > 3 else []

    def count_signals(texts, signals):
        total = 0
        for t in texts:
            t_lower = t.lower()
            total += sum(1 for s in signals if s in t_lower)
        return total

    recent_neg = count_signals(recent, negative_signals)
    recent_pos = count_signals(recent, positive_signals)
    older_neg = count_signals(older, negative_signals) if older else 0
    older_pos = count_signals(older, positive_signals) if older else 0

    trend_multiplier = 1.0
    trend_notes = []

    if len(older) > 0:
        recent_neg_rate = recent_neg / max(len(recent), 1)
        older_neg_rate = older_neg / max(len(older), 1)
        if recent_neg_rate > older_neg_rate * 1.5 and recent_neg >= 3:
            trend_multiplier = 1.3
            trend_notes.append(
                f"Negative signals increasing ({recent_neg_rate:.1f}/entry vs {older_neg_rate:.1f}/entry)"
            )

        recent_pos_rate = recent_pos / max(len(recent), 1)
        older_pos_rate = older_pos / max(len(older), 1)
        if recent_pos_rate < older_pos_rate * 0.5 and older_pos >= 2:
            trend_multiplier = max(trend_multiplier, 1.2)
            trend_notes.append(
                f"Positive signals declining ({recent_pos_rate:.1f}/entry vs {older_pos_rate:.1f}/entry)"
            )

    crisis_entries = sum(
        1 for t in recent if any(kw in t.lower() for kw in ["suicide", "kill myself", "end my life", "want to die"])
    )
    if crisis_entries >= 2:
        trend_multiplier = max(trend_multiplier, 1.5)
        trend_notes.append(f"Crisis language in {crisis_entries}/{len(recent)} recent entries")

    original_score = base_result["risk_score"]
    new_score = min(10, round(original_score * trend_multiplier))
    base_result["risk_score"] = new_score
    base_result["triggered"] = new_score >= CRISIS_POLICY.auto_trigger_threshold

    if trend_notes:
        explanation = base_result.get("explainability", {})
        if isinstance(explanation, str):
            try:
                explanation = json.loads(explanation)
            except Exception:
                explanation = {"notes": explanation}
        explanation["temporal_analysis"] = {
            "trend_multiplier": trend_multiplier,
            "notes": trend_notes,
            "original_score": original_score,
            "adjusted_score": new_score,
        }
        base_result["explainability"] = explanation

    return base_result
