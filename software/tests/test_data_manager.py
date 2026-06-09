import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_db
from data_manager_ import (
    save_journal_entry, get_patient_history, get_all_patient_summaries,
    save_clinical_note, get_clinical_notes,
    load_bookings, save_booking, update_booking_status,
    load_followups, save_followup, update_followup_status, update_followup_grade,
)


class TestJournal:
    def test_save_and_get(self):
        save_journal_entry("test_patient_1", "Feeling great today!", "Positive mood noted")
        history = get_patient_history("test_patient_1")
        assert len(history) >= 1
        assert history[-1]["summary"] == "Positive mood noted"

    def test_multiple_entries(self):
        for i in range(3):
            save_journal_entry("test_patient_2", f"Entry {i}", f"Summary {i}")
        history = get_patient_history("test_patient_2")
        summaries = [e["summary"] for e in history if e["summary"].startswith("Summary")]
        assert len(summaries) == 3

    def test_get_other_patient_empty(self):
        history = get_patient_history("nonexistent")
        assert history == []

    def test_all_summaries(self):
        save_journal_entry("test_patient_1", "Another entry", "Another summary")
        summaries = get_all_patient_summaries()
        assert "test_patient_1" in summaries
        assert len(summaries["test_patient_1"]) >= 1

    def test_entry_order(self):
        save_journal_entry("charlie_order_test", "First", "First summary")
        save_journal_entry("charlie_order_test", "Second", "Second summary")
        history = get_patient_history("charlie_order_test")
        assert len(history) == 2
        assert history[0]["summary"] == "First summary"
        assert history[-1]["summary"] == "Second summary"


class TestClinicalNotes:
    def test_save_and_get(self):
        save_clinical_note("test_psych_1", "test_patient_1", "Patient is improving", "Clinical: improving")
        notes = get_clinical_notes("test_psych_1")
        assert len(notes) >= 1
        assert notes[-1]["ai_synthesis"] == "Clinical: improving"

    def test_notes_by_psychologist(self):
        save_clinical_note("test_psych_2", "test_patient_2", "Needs monitoring", "Clinical: monitor")
        p1_notes = get_clinical_notes("test_psych_1")
        p2_notes = get_clinical_notes("test_psych_2")
        p1_has = any(n["patient"] == "test_patient_1" for n in p1_notes)
        p2_has = any(n["patient"] == "test_patient_2" for n in p2_notes)
        assert p1_has
        assert p2_has

    def test_notes_include_patient(self):
        save_clinical_note("test_psych_1", "test_patient_3", "Test", "Test synthesis")
        notes = get_clinical_notes("test_psych_1")
        p3_notes = [n for n in notes if n["patient"] == "test_patient_3"]
        assert len(p3_notes) >= 1


class TestBookings:
    def test_save_and_load(self):
        save_booking("test_patient_1", "2026-06-10", "10:00", "Therapy", "Noah (65)", "noah@test.com", "Regular session")
        bookings = load_bookings()
        p1_bookings = [b for b in bookings if b["patient"] == "test_patient_1"]
        assert len(p1_bookings) >= 1
        assert p1_bookings[-1]["status"] == "Pending"

    def test_update_status(self):
        save_booking("test_patient_2", "2026-06-11", "14:00", "Follow-up", "Mason (26)", "mason@test.com", "Check-in")
        bookings = load_bookings()
        p2_indices = [i for i, b in enumerate(bookings) if b["patient"] == "test_patient_2"]
        if p2_indices:
            update_booking_status(p2_indices[-1], "Accepted")
            bookings = load_bookings()
            assert bookings[p2_indices[-1]]["status"] == "Accepted"


class TestFollowups:
    def test_save_and_load(self):
        save_followup("test_patient_1", "test_psych_1", "Breathing exercise", "Do 5 min breathing daily")
        tasks = load_followups()
        p1_tasks = [t for t in tasks if t["patient"] == "test_patient_1"]
        assert len(p1_tasks) >= 1
        assert p1_tasks[-1]["title"] == "Breathing exercise"

    def test_update_status(self):
        save_followup("test_patient_2", "test_psych_1", "Journaling", "Write daily")
        tasks = load_followups()
        p2_tasks = [t for t in tasks if t["patient"] == "test_patient_2" and t["title"] == "Journaling"]
        if p2_tasks:
            update_followup_status(p2_tasks[-1]["id"], "completed", "/tmp/proof.txt")
            tasks = load_followups()
            updated = [t for t in tasks if t["id"] == p2_tasks[-1]["id"]]
            assert len(updated) == 1
            assert updated[0]["status"] == "completed"

    def test_update_grade(self):
        save_followup("test_patient_3", "test_psych_2", "Mindfulness", "Practice 10 min")
        tasks = load_followups()
        p3_tasks = [t for t in tasks if t["patient"] == "test_patient_3" and t["title"] == "Mindfulness"]
        if p3_tasks:
            update_followup_grade(p3_tasks[-1]["id"], "green", "Well done!")
            tasks = load_followups()
            graded = [t for t in tasks if t["id"] == p3_tasks[-1]["id"]]
            assert graded[0]["grade"] == "green"
            assert graded[0]["feedback"] == "Well done!"

    def test_default_values(self):
        save_followup("test_patient_1", "test_psych_1", "Default test", "")
        tasks = load_followups()
        dt = [t for t in tasks if t["title"] == "Default test"]
        assert dt[0]["status"] == "pending"
        assert dt[0]["grade"] == "none"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
