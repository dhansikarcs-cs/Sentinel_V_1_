from app.api.patients import derive_priorities
from app.models.ring import RingSensorLog


def _ring(*, bpm=72, stress=35, sleep_hours=7.0, spo2=98):
    return RingSensorLog(bpm=bpm, stress=stress, sleep_hours=sleep_hours, spo2=spo2)


def _baseline():
    return {
        "crisis": None,
        "risk": None,
        "followups": [],
        "changes": {"mood_trend": "stable", "mood_change_pct": 0.0, "journal_count_7": 3, "journal_count_14": 6},
        "ring_logs": [_ring(), _ring(sleep_hours=7.5)],
    }


def test_empty_signals_yield_stable_low_priority():
    items = derive_priorities(**_baseline())
    assert len(items) == 1
    assert items[0]["level"] == "low"
    assert items[0]["title"] == "No urgent items"
    assert items[0]["reason"] and items[0]["evidence"] and items[0]["action"]


def test_active_crisis_is_top_priority():
    ctx = _baseline()
    ctx["crisis"] = {"active": True, "triggered_at": "2026-08-01T10:00:00", "acknowledged": False}
    items = derive_priorities(**ctx)
    assert items[0]["level"] == "high"
    assert items[0]["title"] == "Active crisis"
    assert "NOT acknowledged" in items[0]["evidence"]


def test_triggered_risk_is_high():
    ctx = _baseline()
    ctx["risk"] = {"risk_score": 9, "triggered": True, "algorithm_version": "1", "confidence": 0.9}
    items = derive_priorities(**ctx)
    assert items[0]["level"] == "high"
    assert items[0]["title"] == "Crisis-level risk (9/10)"
    assert "confidence 90%" in items[0]["evidence"]


def test_elevated_risk_medium():
    ctx = _baseline()
    ctx["risk"] = {"risk_score": 6, "triggered": False, "algorithm_version": "1", "confidence": 0.8}
    items = derive_priorities(**ctx)
    assert items[0]["level"] == "medium"
    assert items[0]["title"] == "Rising risk score (6/10)"


def test_overdue_followup_escalates_with_age():
    from datetime import UTC, datetime, timedelta

    ctx = _baseline()
    assigned = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    ctx["followups"] = [{"id": "f1", "status": "pending", "title": "Daily reflection", "assigned_at": assigned}]
    items = derive_priorities(**ctx)
    assert items[0]["title"] == "Follow-up overdue (8d)"
    assert items[0]["level"] == "high"


def test_recent_pending_followup_not_flagged():
    ctx = _baseline()
    ctx["followups"] = [
        {"id": "f1", "status": "pending", "title": "Daily reflection", "assigned_at": "2026-08-02T09:00:00"}
    ]
    items = derive_priorities(**ctx)
    assert all("Follow-up overdue" not in i["title"] for i in items)


def test_mood_declining_medium():
    ctx = _baseline()
    ctx["changes"] = {
        "mood_trend": "declining",
        "mood_change_pct": -35.0,
        "current_mood_avg": 2.0,
        "previous_mood_avg": 3.1,
        "journal_count_7": 3,
        "journal_count_14": 6,
    }
    items = derive_priorities(**ctx)
    assert any(i["title"] == "Mood declining" and i["level"] == "medium" and "35.0%" in i["reason"] for i in items)


def test_sleep_drop_flagged():
    ctx = _baseline()
    ctx["ring_logs"] = [_ring(sleep_hours=5.0), _ring(sleep_hours=7.5)]
    items = derive_priorities(**ctx)
    assert any(i["title"] == "Sleep dropped" and "7.5h → 5.0h" in i["evidence"] for i in items)


def test_priority_ordering_high_first():
    ctx = _baseline()
    ctx["crisis"] = {"active": True, "triggered_at": "2026-08-01T10:00:00", "acknowledged": True}
    ctx["changes"] = {
        "mood_trend": "declining",
        "mood_change_pct": -20.0,
        "current_mood_avg": 2.5,
        "previous_mood_avg": 3.1,
        "journal_count_7": 3,
        "journal_count_14": 6,
    }
    items = derive_priorities(**ctx)
    assert items[0]["level"] == "high"
    assert items[1]["level"] == "medium"
