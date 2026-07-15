"""Demonstrate journal + explainability flow with realistic I/O."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai_kernel_ import summarize_journal, get_emotion_labels, assess_crisis_risk
from data_manager_ import save_journal_entry, get_patient_history
from database import get_db, _run_migrations

# Ensure test user exists
with get_db() as db:
    _run_migrations(db)
    existing = db.execute("SELECT username FROM patient_profiles WHERE username = ?", ("demo_user",)).fetchone()
    if not existing:
        db.execute("INSERT INTO patient_profiles (username, password_hash, name, role) VALUES (?, ?, ?, ?)",
                   ("demo_user", "hash", "Demo User", "patient"))

# ── Demo 1: Normal journal entry ──
print("=" * 60)
print("DEMO 1: Patient saves a journal entry")
print("=" * 60)
raw = "I felt really anxious about my presentation today. My heart was racing before the meeting but once I started speaking it got better. Still feeling a bit shaky."
print(f"\nINPUT (patient writes):")
print(f'  "{raw}"')
print()

result = summarize_journal(raw, mode="patient")
print(f"OUTPUT (AI summary + metadata):")
print(f"  Summary text: {result['text']}")
print(f"  AI Source:    {result['source'].title()}")
print(f"  Emotions:     {result['emotions']}")
print()

# Save to DB with all metadata
save_journal_entry("demo_user", raw, result["text"], result["source"], result["emotions"])
print("  → Saved to DB with ai_source, emotions columns ✓")

# ── Demo 2: Past entries show emotions + source ──
print()
print("=" * 60)
print("DEMO 2: Past entries display (what patient sees)")
print("=" * 60)
entries = get_patient_history("demo_user")
for e in entries[-3:]:
    print(f"\n  Timestamp: {e['timestamp'][:16]}")
    print(f"  Source:    [{e.get('ai_source', '?').title()}]")
    print(f"  Emotions:  {e.get('emotions', '-')}")
    print(f"  Summary:   {e['summary'][:100]}...")

# ── Demo 3: Crisis risk assessment on raw journal ──
print()
print("=" * 60)
print("DEMO 3: Crisis risk assessment (psych triage view)")
print("=" * 60)
crisis_text = "I feel completely hopeless. Nothing matters anymore and I keep thinking about suicide. I can't do this anymore."
print(f"\nINPUT (patient journal):")
print(f'  "{crisis_text[:80]}..."')
print()

risk = assess_crisis_risk(crisis_text)
print(f"OUTPUT (assess_crisis_risk):")
print(f"  Risk score: {risk['risk_score']}/10")
print(f"  Triggered:  {risk['triggered']}")
print(f"  Reasoning:  {risk['reasoning']}")

# ── Demo 4: Low-risk assessment ──
print()
low_text = "Had a lovely walk in the park today. The weather was nice and I felt calm."
print(f"\nINPUT (patient journal):")
print(f'  "{low_text}"')
print()
risk2 = assess_crisis_risk(low_text)
print(f"OUTPUT:")
print(f"  Risk score: {risk2['risk_score']}/10")
print(f"  Triggered:  {risk2['triggered']}")
print(f"  Reasoning:  {risk2['reasoning']}")

# ── Demo 5: Clinical mode (psychologist view) ──
print()
print("=" * 60)
print("DEMO 5: Clinical mode (psychologist sees patient journal)")
print("=" * 60)
print(f"\nINPUT (same journal, clinical mode):")
print(f'  "{raw[:80]}..."')
print()
clinical = summarize_journal(raw, mode="clinical")
print(f"OUTPUT:")
print(f"  Clinical summary: {clinical['text']}")
print(f"  Source:           {clinical['source'].title()}")
print(f"  Emotions:         {clinical['emotions']}")

# ── Demo 6: Source label styles ──
print()
print("=" * 60)
print("DEMO 6: Source badge colors (what users see)")
print("=" * 60)
sources = {
    "ollama": "#c49ea4 (rose-mauve)  — local LLM",
    "groq":  "#22c55e  (green)       — cloud API fallback",
    "rule":  "#f59e0b  (amber)       — keyword fallback",
}
for src, desc in sources.items():
    print(f"  [{src.title():7s}] → {desc}")

print()
print("=" * 60)
print("ALL DEMOS COMPLETE")
print("=" * 60)
