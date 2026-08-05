from app.ml.crisis_policy import CRISIS_POLICY
from app.ml.risk_engine import (
    _emotion_risk_contribution,
    _keyword_risk_score,
    assess_risk_with_explainability,
    assess_risk_with_history,
)

NEUTRAL_PROBS = {"neutral": 0.9, "joy": 0.05, "curiosity": 0.05}


def test_crisis_keyword_scores_max_and_triggers():
    result = assess_risk_with_explainability("I want to die, this is an emergency", NEUTRAL_PROBS)
    assert result["risk_score"] == 10
    assert result["triggered"] is True
    assert "want to die" in result["explainability"]["keyword_signals"]["crisis_keywords"]


def test_high_risk_keyword_lands_in_high_band_without_trigger():
    result = assess_risk_with_explainability("I feel totally hopeless and desperate", NEUTRAL_PROBS)
    assert result["risk_score"] >= 7
    assert result["risk_score"] < CRISIS_POLICY.auto_trigger_threshold or result["triggered"] is False
    assert result["explainability"]["keyword_base_score"] == 7


def test_moderate_keyword_lands_in_medium_band():
    result = assess_risk_with_explainability("I am sad and worried about everything", NEUTRAL_PROBS)
    assert 4 <= result["risk_score"] <= 6


def test_blank_text_scores_low_and_never_triggers():
    for text in ("", "   "):
        result = assess_risk_with_explainability(text)
        assert result["risk_score"] == 1
        assert result["triggered"] is False


def test_social_withdrawal_raises_score():
    baseline = assess_risk_with_explainability("I felt okay today", NEUTRAL_PROBS)
    withdrawal = assess_risk_with_explainability(
        "I am alone. Nobody talks to me, no one cares, I isolated myself", NEUTRAL_PROBS
    )
    assert withdrawal["risk_score"] > baseline["risk_score"]
    assert withdrawal["explainability"]["keyword_signals"]["social_withdrawal_count"] >= 2


def test_emotion_contribution_is_scored_and_explained():
    probs = {"fear": 0.7, "neutral": 0.3}
    analysis = _emotion_risk_contribution(probs)
    assert analysis["emotion_risk_score"] > 0
    assert analysis["top_contributors"][0]["emotion"] == "fear"
    result = assess_risk_with_explainability("ordinary text with no keywords at all", probs)
    assert "Primary emotion signal: fear" in result["reasoning"]


def test_explainability_exposes_decision_factors():
    result = assess_risk_with_explainability("panic and anxiety, can't breathe", NEUTRAL_PROBS)
    facts = result["explainability"]
    assert set(facts) >= {"emotion_risk_score", "keyword_base_score", "blended_score", "keyword_signals"}


def test_history_escalates_with_recent_worsening_trend():
    text = "I feel hopeless and desperate today"
    stable_history = ["I felt fine today", "Everything is okay", "A normal day"]
    worsening_history = [
        "Everything felt fine and calm today",
        "I feel a bit tired",
        "I feel hopeless and worthless",
        "I can't sleep, nightmare last night, crying and numb",
    ]
    baseline = assess_risk_with_history(text, recent_texts=stable_history)
    escalated = assess_risk_with_history(text, recent_texts=worsening_history)
    assert escalated["risk_score"] > baseline["risk_score"]
    assert escalated["explainability"]["temporal_analysis"]["trend_multiplier"] >= 1.3
    assert escalated["risk_score"] >= 8


def test_history_short_series_does_not_change_base():
    text = "I am sad"
    short = assess_risk_with_history(text, recent_texts=["a", "b"])
    base = assess_risk_with_explainability(text)
    assert short["risk_score"] == base["risk_score"]


def test_keyword_counting_is_robust_to_case():
    kw = _keyword_risk_score("PANIC PANIC PANIC CAN'T BREATHE")
    assert len(kw["high_risk_keywords"]) > 0
    assert kw["base_score"] == 7


def test_policy_band_boundaries():
    assert CRISIS_POLICY.triage_priority(3) == "low"
    assert CRISIS_POLICY.triage_priority(4) == "medium"
    assert CRISIS_POLICY.triage_priority(6) == "medium"
    assert CRISIS_POLICY.triage_priority(7) == "high"
    assert CRISIS_POLICY.should_auto_trigger(8, triggered=True) is True
    assert CRISIS_POLICY.should_auto_trigger(7, triggered=True) is False
    assert CRISIS_POLICY.should_notify(7) is True
    assert CRISIS_POLICY.should_notify(6) is False
