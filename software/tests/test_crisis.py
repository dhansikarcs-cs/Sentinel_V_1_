import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_db
from data_manager_ import get_crisis_state, set_crisis_state, load_crisis_log, append_crisis_log


class TestCrisisState:
    def test_default_state(self):
        state = get_crisis_state()
        assert "active" in state
        assert "patient" in state

    def test_set_crisis_state(self):
        state = {
            "active": True, "patient": "test_patient_1", "triggered_at": datetime.now().isoformat(),
            "triggered_by": "patient", "acknowledged": False, "acknowledged_by": "",
            "acknowledged_at": "", "helpline_escalated": False,
            "trusted_contact_notified": False, "trustee_acknowledged": False,
            "trustee_clicked": False, "tc_ack_emailed": False, "helpline_ack_emailed": False,
        }
        set_crisis_state(state)
        loaded = get_crisis_state()
        assert loaded["active"] is True
        assert loaded["patient"] == "test_patient_1"
        assert loaded["triggered_by"] == "patient"

    def test_update_crisis_state(self):
        state = get_crisis_state()
        state["acknowledged"] = True
        state["acknowledged_by"] = "test_psych_1"
        set_crisis_state(state)
        loaded = get_crisis_state()
        assert loaded["acknowledged"] is True
        assert loaded["acknowledged_by"] == "test_psych_1"

    def test_resolve_crisis(self):
        state = get_crisis_state()
        state["active"] = False
        state["patient"] = ""
        set_crisis_state(state)
        loaded = get_crisis_state()
        assert loaded["active"] is False

    def test_multiple_crisis_updates_idempotent(self):
        for _ in range(5):
            s = get_crisis_state()
            s["active"] = True
            s["patient"] = "test_patient_2"
            set_crisis_state(s)
        loaded = get_crisis_state()
        assert loaded["active"] is True
        assert loaded["patient"] == "test_patient_2"


class TestCrisisLog:
    def test_empty_log(self):
        log = load_crisis_log()
        assert isinstance(log, list)

    def test_append_entry(self):
        entry = {"event": "triggered", "patient": "test_patient_1", "timestamp": datetime.now().isoformat(), "source": "patient"}
        append_crisis_log(entry)
        log = load_crisis_log()
        assert len(log) >= 1
        assert log[-1]["event"] == "triggered"

    def test_append_multiple(self):
        for i in range(3):
            append_crisis_log({"event": f"test_{i}", "patient": "test_patient_1", "timestamp": datetime.now().isoformat()})
        log = load_crisis_log()
        events = [e["event"] for e in log if e["event"].startswith("test_")]
        assert len(events) == 3

    def test_log_with_details(self):
        append_crisis_log({
            "event": "vitals_ai", "patient": "test_patient_3",
            "timestamp": datetime.now().isoformat(),
            "details": {"base_hr": 72, "spike_hr": 96, "risk_score": 8},
        })
        log = load_crisis_log()
        last = log[-1]
        if isinstance(last.get("details"), dict):
            assert last["details"].get("risk_score") == 8


if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
