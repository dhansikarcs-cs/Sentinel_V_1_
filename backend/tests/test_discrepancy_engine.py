"""Unit tests for the text-biometric discrepancy engine (_detect)."""

from app.api.discrepancy import _detect


def test_depressive_vocabulary_is_negative():
    for text in [
        "feeling worthless and guilty about everything",
        "That familiar heaviness again. Didn't sleep well.",
        "Cried for hours without really knowing why.",
        "Felt like a burden to everyone around me.",
        "Woke up at 4am replaying old mistakes. Ruminating again.",
        "Couldn't get out of bed until noon. Canceled plans again.",
    ]:
        _disc, sentiment, bio, _ = _detect(text, 72, 40)
        assert sentiment == "negative", text


def test_anymore_false_positive():
    disc, sentiment, bio, _ = _detect("Nothing brings me joy anymore.", 72, 40)
    assert sentiment == "negative"
    assert disc is False


def test_negated_positive_flips_to_negative():
    for text in [
        "I am not happy today",
        "I am not feeling great at all",
        "I don't trust the good moments",
    ]:
        disc, sentiment, bio, _ = _detect(text, 72, 40)
        assert sentiment == "negative", text


def test_double_negation_is_neutral():
    disc, sentiment, bio, _ = _detect("I am not feeling terrible today", 72, 60)
    assert sentiment == "neutral"


def test_cant_stop_idiom_preserves_emotion():
    disc, sentiment, bio, _ = _detect("I can't stop laughing", 72, 40)
    assert sentiment == "positive"

    disc, sentiment, bio, _ = _detect("I can't stop crying", 72, 40)
    assert sentiment == "negative"


def test_anymore_does_not_neutralize_cant():
    # P34 from the benchmark set: "I can't handle this anymore" + high stress.
    disc, sentiment, bio, _ = _detect("I can't handle this anymore", 135, 13)
    assert sentiment == "negative"
    assert bio == "high_stress"
    assert disc is False


def test_cross_window_negation_does_not_bleed():
    disc, sentiment, bio, _ = _detect(
        "not feeling great today but actually today was better", 60, 30
    )
    assert sentiment == "neutral"


def test_substring_matching_no_false_fire():
    disc, sentiment, bio, _ = _detect("I was dying my hair", 72, 40)
    assert sentiment == "neutral"


def test_discrepancy_fires_for_each_direction():
    assert _detect("I am hopeless and alone", 60, 60)[0] is True
    assert _detect("I am so happy and great", 120, 20)[0] is True
    assert _detect("I walked to the store today", 120, 20)[0] is True


def test_discrepancy_controls_do_not_fire():
    assert _detect("I am hopeless and alone", 120, 20)[0] is False
    assert _detect("I am so happy and great", 60, 60)[0] is False
    assert _detect("I walked to the store today", 72, 40)[0] is False
