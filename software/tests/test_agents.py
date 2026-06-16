import os, sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_db
from data_manager_ import save_booking, save_followup, save_journal_entry, load_bookings
from agent_ import suggest_slots, draft_followup, journal_to_note, _detect_themes, _match_therapies


class TestDetectThemes:
    def test_anxiety_theme(self):
        assert "anxiety" in _detect_themes("I feel very anxious and panicked today")

    def test_mood_theme(self):
        assert "mood" in _detect_themes("I feel so sad and hopeless")

    def test_crisis_theme(self):
        assert "crisis" in _detect_themes("I want to die, I can't do this anymore")

    def test_sleep_theme(self):
        assert "sleep" in _detect_themes("Can't sleep at all, insomnia is killing me")

    def test_stress_theme(self):
        assert "stress" in _detect_themes("Overwhelmed with work deadlines and pressure")

    def test_general_fallback(self):
        assert _detect_themes("Had a nice day today") == ["general"]

    def test_multiple_themes(self):
        t = _detect_themes("Anxious and sad, can't sleep from stress")
        assert "anxiety" in t
        assert "mood" in t
        assert "sleep" in t
        assert "stress" in t


class TestMatchTherapies:
    def test_anxiety_matches_cbt_and_mindfulness(self):
        m = _match_therapies(["anxiety"], "feeling very anxious and panicked")
        assert any("CBT" in t for t in m)
        assert any("Mindfulness" in t for t in m)

    def test_crisis_matches_dbt(self):
        m = _match_therapies(["crisis"], "feeling suicidal")
        assert any("DBT" in t for t in m)

    def test_sleep_matches_sleep_hygiene(self):
        m = _match_therapies(["sleep"], "can't sleep at night")
        assert any("Sleep Hygiene" in t for t in m)

    def test_returns_max_4(self):
        m = _match_therapies(["anxiety", "mood", "sleep", "stress"], "anxious sad tired stressed")
        assert len(m) <= 4


class TestSuggestSlots:
    def test_returns_dict_with_required_keys(self):
        r = suggest_slots("test_patient_1")
        assert r["patient"] == "test_patient_1"
        assert "suggested_slots" in r
        assert "priority" in r
        assert "urgency_score" in r
        assert "reasoning" in r

    def test_suggests_3_slots(self):
        r = suggest_slots("test_patient_1")
        assert len(r["suggested_slots"]) == 3

    def test_each_slot_has_date_time_day(self):
        r = suggest_slots("test_patient_1")
        for s in r["suggested_slots"]:
            assert "date" in s
            assert "time" in s
            assert "day" in s
            assert "label" in s

    def test_dates_are_in_the_future(self):
        r = suggest_slots("test_patient_1")
        today = datetime.now()
        for s in r["suggested_slots"]:
            d = datetime.strptime(s["date"], "%Y-%m-%d")
            assert d >= today.replace(hour=0, minute=0, second=0, microsecond=0)

    def test_high_urgency_patient(self):
        with get_db() as db:
            db.execute("DELETE FROM followups WHERE patient_username='unique_test_patient'")
            for _ in range(3):
                db.execute(
                    "INSERT INTO followups (patient_username, psychologist_username, title, description, status, grade) VALUES (?,?,?,?,?,?)",
                    ("unique_test_patient", "test_psych_1", "x", "x", "not_yet", "red"),
                )
        r = suggest_slots("unique_test_patient")
        with get_db() as db:
            db.execute("DELETE FROM followups WHERE patient_username='unique_test_patient'")
        assert r["urgency_score"] >= 5


class TestDraftFollowup:
    def test_returns_dict_with_required_keys(self):
        r = draft_followup("test_patient_1")
        assert "tasks" in r
        assert "reasoning" in r
        assert "patient" in r

    def test_returns_at_least_1_task(self):
        r = draft_followup("test_patient_1")
        assert len(r["tasks"]) >= 1

    def test_each_task_has_title_and_description(self):
        r = draft_followup("test_patient_1")
        for t in r["tasks"]:
            assert "title" in t
            assert "description" in t

    def test_crisis_journal_returns_urgent_task(self):
        with get_db() as db:
            db.execute("DELETE FROM journal_entries WHERE patient_username='unique_test_patient'")
            db.execute(
                "INSERT INTO journal_entries (patient_username, raw_content, summary, timestamp) VALUES (?,?,?,?)",
                ("unique_test_patient", "I feel like ending my life. Everything is hopeless and I want to disappear.",
                 "Suicidal ideation", datetime.now().isoformat()),
            )
        r = draft_followup("unique_test_patient")
        with get_db() as db:
            db.execute("DELETE FROM journal_entries WHERE patient_username='unique_test_patient'")
        titles = " ".join(t["title"] for t in r["tasks"])
        assert any(w in titles.lower() for w in ["safety", "urgent", "crisis"])


class TestJournalToNote:
    def test_returns_dict_with_required_keys(self):
        r = journal_to_note("test_patient_1", "I feel very anxious and stressed today")
        assert "suggestion" in r
        assert "themes" in r
        assert "matched_therapies" in r
        assert "patient" in r

    def test_detects_anxiety_theme(self):
        r = journal_to_note("test_patient_1", "Panic attacks and constant worry about everything")
        assert "anxiety" in r["themes"]

    def test_note_contains_sections(self):
        r = journal_to_note("test_patient_1", "Feeling depressed and lonely")
        text = r["suggestion"]
        assert len(text) > 50
        assert any(w in text.lower() for w in ["patient", "assessment", "plan", "report", "clinical"])

    def test_source_is_rule_by_default(self):
        r = journal_to_note("test_patient_1", "Normal day")
        assert r["source"] in ("rule", "ai")

    def test_uses_summary_when_provided(self):
        r = journal_to_note("test_patient_1", "raw text here", summary="Patient reports feeling anxious about work presentations. Notes increased heart rate before meetings and difficulty sleeping the night before. Describes catastrophic thoughts about failure.")
        assert r["source"] in ("rule", "ai")
        assert "work presentations" in r["suggestion"] or "heart rate" in r["suggestion"]

    def test_crisis_text_returns_crisis_assessment(self):
        r = journal_to_note("test_patient_1", "I want to end my life, nothing matters anymore")
        text = r["suggestion"].upper()
        assert any(w in text for w in ["CRISIS", "SUICID", "HIGH RISK", "IMMEDIAT"])

    def test_matched_therapies_includes_cbt(self):
        r = journal_to_note("test_patient_1", "I keep having negative thoughts and can't stop worrying")
        assert any("CBT" in t for t in r["matched_therapies"])


if __name__ == "__main__":
    import pytest
    pytest.main([__file__])


class TestRingVitalsRisk:
    def test_normal_vitals_low_risk(self):
        from agent_ import ring_vitals_risk
        r = ring_vitals_risk({"bpm": 72, "spo2": 97, "stress": 35})
        assert r["risk"] == "low"
        assert r["flags"] == []

    def test_high_bpm_tachycardia(self):
        from agent_ import ring_vitals_risk
        r = ring_vitals_risk({"bpm": 90, "spo2": 97, "stress": 35})
        assert "elevated_hr" in r["flags"]

    def test_very_high_bpm(self):
        from agent_ import ring_vitals_risk
        r = ring_vitals_risk({"bpm": 120, "spo2": 97, "stress": 35})
        assert "tachycardia" in r["flags"]

    def test_low_spo2(self):
        from agent_ import ring_vitals_risk
        r = ring_vitals_risk({"bpm": 72, "spo2": 90, "stress": 35})
        assert "hypoxia" in r["flags"]

    def test_high_stress(self):
        from agent_ import ring_vitals_risk
        r = ring_vitals_risk({"bpm": 72, "spo2": 97, "stress": 80})
        assert "high_stress" in r["flags"]

    def test_multiple_flags_high_risk(self):
        from agent_ import ring_vitals_risk
        r = ring_vitals_risk({"bpm": 110, "spo2": 91, "stress": 80})
        assert r["risk"] == "high"
        assert len(r["flags"]) >= 2
