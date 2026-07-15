"""Seed demo data: follow-ups, booking, clinical notes for cel"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'software'))
from data_manager_ import _ensure_migrated
from database import get_db
from datetime import datetime, timedelta

_ensure_migrated()
today = datetime.now()

with get_db() as db:
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    table_names = [t["name"] for t in tables]
    print("Tables:", table_names)

    # Seed follow-ups for cel
    if "followups" in table_names:
        tasks = [
            ("cel", "alaya", "Practice 5-5-5 breathing", "completed", "green", (today - timedelta(days=2)).isoformat()),
            ("cel", "alaya", "Daily mood log", "completed", "yellow", (today - timedelta(days=1)).isoformat()),
            ("cel", "alaya", "Sleep hygiene tracker", "pending", "none", (today + timedelta(days=1)).isoformat()),
            ("cel", "alaya", "Anxiety management log", "completed", "red", (today - timedelta(days=3)).isoformat()),
            ("cel", "alaya", "Guided reflection journal", "not_yet", "none", (today - timedelta(days=4)).isoformat()),
        ]
        for patient, psych, title, status, grade, ts in tasks:
            existing = db.execute("SELECT id FROM followups WHERE patient_username = ? AND title = ?", (patient, title)).fetchone()
            if not existing:
                db.execute("INSERT INTO followups (patient_username, psychologist_username, title, description, status, grade, created_at) VALUES (?,?,?,?,?,?,?)",
                           (patient, psych, title, f"Task: {title}", status, grade, ts))
        print(f"Seeded {len(tasks)} follow-ups")
    else:
        print("No followups table")

    # Seed booking
    if "bookings" in table_names:
        existing_book = db.execute("SELECT id FROM bookings WHERE patient_username = ?", ("cel",)).fetchone()
        if not existing_book:
            db.execute("INSERT INTO bookings (patient_username, psychologist_username, date, time, status, notes) VALUES (?,?,?,?,?,?)",
                       ("cel", "alaya", (today + timedelta(days=2)).strftime("%Y-%m-%d"), "10:00", "Pending", "Initial session"))
            print("Seeded booking")
        else:
            print("Booking already exists")
    else:
        print("No bookings table")

    # Seed clinical note
    if "clinical_notes" in table_names:
        existing_note = db.execute("SELECT id FROM clinical_notes WHERE patient_username = ?", ("cel",)).fetchone()
        if not existing_note:
            db.execute("INSERT INTO clinical_notes (psychologist_username, patient_username, raw_notes, ai_synthesis, timestamp) VALUES (?,?,?,?,?)",
                       ("alaya", "cel", "Patient presents with moderate anxiety and sleep disturbance. Responding well to CBT-I techniques.",
                        "Anxiety management with sleep hygiene focus. Continue monitoring.", today.isoformat()))
            print("Seeded clinical note")
        else:
            print("Clinical note already exists")
    else:
        print("No clinical_notes table")
