import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai_kernel_ import get_emotion_labels, summarize_journal, assess_crisis_risk
from data_manager_ import save_journal_entry, get_patient_history, get_all_patient_summaries
from database import get_db, _run_migrations


def test_get_emotion_labels_exists():
    labels = get_emotion_labels("I feel sad and anxious")
    assert isinstance(labels, str)


def test_summarize_journal_returns_dict_patient():
    result = summarize_journal("Had a rough day. Stressed about work.", "patient")
    assert isinstance(result, dict)
    assert "text" in result
    assert "source" in result
    assert "emotions" in result
    assert result["source"] in ("ollama", "groq", "rule", "")
    assert isinstance(result["text"], str)
    assert len(result["text"]) > 0


def test_summarize_journal_returns_dict_clinical():
    result = summarize_journal("Feeling overwhelmed with deadlines.", "clinical")
    assert isinstance(result, dict)
    assert "text" in result and "source" in result and "emotions" in result


def test_summarize_journal_empty():
    result = summarize_journal("")
    assert result["source"] == ""
    assert result["emotions"] == ""
    assert result["text"] == "No content to summarize."


def test_assess_crisis_risk_high():
    risk = assess_crisis_risk("I want to kill myself. Nothing matters anymore.")
    assert "risk_score" in risk
    assert "reasoning" in risk
    assert "triggered" in risk
    assert risk["triggered"] is True
    assert risk["risk_score"] >= 8


def test_assess_crisis_risk_low():
    risk = assess_crisis_risk("Had a nice day, feeling okay.")
    assert risk["risk_score"] <= 4


def test_assess_crisis_risk_empty():
    risk = assess_crisis_risk("")
    assert risk["risk_score"] == 1
    assert risk["triggered"] is False


def test_db_save_retrieve_new_columns():
    with get_db() as db:
        _run_migrations(db)
        existing = db.execute(
            "SELECT username FROM patient_profiles WHERE username = ?", ("explain_test",)
        ).fetchone()
        if not existing:
            db.execute(
                "INSERT INTO patient_profiles (username, password_hash, name, role) VALUES (?, ?, ?, ?)",
                ("explain_test", "test-hash", "Explain Test", "patient")
            )
    save_journal_entry("explain_test", "Test raw content", "Test summary", "ollama", "sadness, stress")
    entries = get_patient_history("explain_test")
    last = entries[-1]
    assert last.get("ai_source") == "ollama"
    assert last.get("emotions") == "sadness, stress"


def test_all_summaries_includes_new_columns():
    with get_db() as db:
        _run_migrations(db)
        existing = db.execute(
            "SELECT username FROM patient_profiles WHERE username = ?", ("explain_test2",)
        ).fetchone()
        if not existing:
            db.execute(
                "INSERT INTO patient_profiles (username, password_hash, name, role) VALUES (?, ?, ?, ?)",
                ("explain_test2", "test-hash", "Explain Test 2", "patient")
            )
    save_journal_entry("explain_test2", "Raw", "Sum", "groq", "fear")
    all_s = get_all_patient_summaries()
    assert "explain_test2" in all_s
    latest = all_s["explain_test2"][-1]
    assert latest.get("ai_source") == "groq"
    assert latest.get("emotions") == "fear"
