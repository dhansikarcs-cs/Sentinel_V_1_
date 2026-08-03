import dataclasses

import pytest

from app.ml.crisis_policy import CRISIS_POLICY, CrisisPolicy


def test_default_policy_thresholds():
    policy = CRISIS_POLICY
    assert policy.auto_trigger_threshold == 8
    assert policy.notify_threshold == 7
    assert policy.warn_threshold == 6
    assert policy.elevated_alert_threshold == 7


def test_triage_priority_bands():
    policy = CrisisPolicy()
    assert policy.triage_priority(1) == "low"
    assert policy.triage_priority(3) == "low"
    assert policy.triage_priority(4) == "medium"
    assert policy.triage_priority(6) == "medium"
    assert policy.triage_priority(7) == "high"
    assert policy.triage_priority(10) == "high"


def test_should_auto_trigger():
    policy = CrisisPolicy()
    assert policy.should_auto_trigger(8, triggered=True)
    assert policy.should_auto_trigger(10, triggered=True)
    assert not policy.should_auto_trigger(8, triggered=False)
    assert not policy.should_auto_trigger(7, triggered=True)
    assert not policy.should_auto_trigger(7, triggered=False)


def test_should_notify():
    policy = CrisisPolicy()
    assert policy.should_notify(7)
    assert policy.should_notify(8)
    assert not policy.should_notify(6)


def test_should_warn():
    policy = CrisisPolicy()
    assert policy.should_warn(6)
    assert not policy.should_warn(5)


def test_should_elevate_alert():
    policy = CrisisPolicy()
    assert policy.should_elevate_alert(7)
    assert not policy.should_elevate_alert(6)


def test_action_messages_are_formatable():
    messages = CRISIS_POLICY.action_messages()
    assert "risk score of 9/10" in messages["notify"].format(risk_score=9)
    assert "journal #12" in messages["auto_trigger"].format(risk_score=9, journal_id=12, delay=30)
    assert "30s" in messages["auto_trigger"].format(risk_score=9, journal_id=12, delay=30)
    assert "alice" in messages["auto_trigger_alert"].format(patient="alice", risk_score=9)
    assert "alice" in messages["risk_warning_alert"].format(patient="alice", risk_score=7)


def test_frozen_policy_cannot_be_mutated():
    with pytest.raises(dataclasses.FrozenInstanceError):
        CRISIS_POLICY.auto_trigger_threshold = 9
