"""Sentinel DB reset + demo seed.
Deletes ALL existing users and data, then creates exactly two accounts:
  - cel  (psychologist) / 1234
  - alaya (patient)     / 4321
Plus rich demo data (journals, moods, ring, bookings, followups,
clinical notes, notifications, psych journal, risk assessments).

Journal summaries are dual-mode:
  - patient summary  -> warm, motivating, validating
  - clinical summary -> clinical, third-person, structured
"""

import json
import os
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta

sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.booking import Booking
from app.models.clinical_note import ClinicalNote
from app.models.crisis import CrisisState
from app.models.followup import FollowupTask
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.notification import Notification
from app.models.psych_journal import PsychJournalEntry
from app.models.ring import RingSensorLog
from app.models.risk_assessment import RiskAssessment
from app.models.user import User

now = datetime.now(UTC)

# ── 1. DELETE EVERYTHING ──────────────────────────────────────
print("=== DELETING ALL EXISTING DATA ===")
Base.metadata.create_all(bind=engine)
insp = inspect(engine)
tables = insp.get_table_names()
# drop in reverse FK-safe order (simple: delete all rows)
ordered = [
    "risk_assessments",
    "ai_analyses",
    "emotion_results",
    "sensor_readings",
    "psych_journal_entries",
    "clinical_notes",
    "notifications",
    "triage_queue",
    "crisis_logs",
    "crisis_states",
    "followups",
    "bookings",
    "psych_availability",
    "ring_sensor_log",
    "mood_log",
    "journal_entries",
    "patient_profiles",
    "audit_logs",
    "event_store",
]
with engine.begin() as conn:
    for t in ordered:
        if t in tables:
            conn.execute(text(f'DELETE FROM "{t}"'))
            print(f"  cleared: {t}")
print()

db = SessionLocal()


def salt():
    return os.urandom(16).hex()


# ── 2. ACCOUNTS ────────────────────────────────────────────────
print("=== CREATING ACCOUNTS ===")
cel = User(
    username="cel",
    password_hash=hash_password("1234"),
    name="Dr. Celeste R.",
    role="psychologist",
    clinic_code="DEMO",
    onboarding_step=99,
    contact_info="cel@sentinel.demo",
    psych_trusted_contact="trusted-cel@sentinel.demo",
    encryption_salt=salt(),
    created_at=now.isoformat(),
)
alaya = User(
    username="alaya",
    password_hash=hash_password("4321"),
    name="Alaya",
    role="patient",
    clinic_code="DEMO",
    onboarding_step=99,
    contact_info="alaya@sentinel.demo",
    trusted_contact="mom@sentinel.demo",
    assigned_psych="cel",
    encryption_salt=salt(),
    created_at=now.isoformat(),
)
db.add_all([cel, alaya])
db.commit()
print("  psych: cel / 1234")
print("  patient: alaya / 4321")
print()

# ── 3. JOURNALS (patient + clinical summaries) ────────────────
print("=== SEEDING JOURNALS ===")
journals = [
    {
        "content": "Today was actually good. I woke up before my alarm, made myself a proper breakfast, and went for a walk near the lake. The air was fresh and for a while I just felt... okay. Like things might be fine.",
        "emotions": "calm, hopeful, grateful",
        "patient": "Okay that sounds like a genuinely great day! Waking up before your alarm AND a proper breakfast? Look at you, out here winning. That lakeside walk sounds lovely, honestly. Hang onto this feeling!",
        "clinical": "Patient reports a positive day: adequate sleep, independent morning routine (breakfast, lakeside walk). Affect congruent, low physiological arousal. Sustained engagement in activities of daily living. Continue reinforcement of routine.",
    },
    {
        "content": "Skipped lunch because my stomach was in knots. That project deadline is breathing down my neck and I keep going over the same scenario in my head. My chest feels tight even now.",
        "emotions": "anxious, nervous, overwhelmed",
        "patient": "Ugh, that knot-in-your-stomach feeling is the absolute worst. You carried all of that by yourself today and that's genuinely heavy. Take it easy on yourself tonight, yeah? We'll get through that deadline one small step at a time.",
        "clinical": "Patient endorses somatic anxiety (gastrointestinal distress, chest tightness) and cognitive rumination linked to work deadline. Moderate sympathetic arousal. No safety concerns. Recommend relaxation training + cognitive restructuring re: catastrophizing.",
    },
    {
        "content": "Session with Dr. Cel went well today. She pointed out a pattern I keep missing: I predict the worst, then the worst never happens, but I still don't give myself credit. That felt seen.",
        "emotions": "relieved, hopeful, grateful",
        "patient": "Yesss, now that's a solid session! It hits different when someone actually *sees* your patterns, right? That 'predict the worst, worst never happens' thing is a real lightbulb moment. Give yourself credit for it — you earned it.",
        "clinical": "Positive therapeutic engagement. Patient demonstrated insight into cognitive distortion (catastrophizing with subsequent disconfirmation). Increased insight and treatment alliance. Progress noted; continue CBT framework.",
    },
    {
        "content": "Couldn't sleep again. Lay there replaying a conversation from three years ago that nobody else even remembers. 3 AM brain is a liar, I know that, but it's loud.",
        "emotions": "anxious, tired, sad",
        "patient": "3AM brain really does love replaying old tapes, doesn't it? Ugh. For what it's worth, that voice is full of lies — and you KNOW that, which honestly says a lot about how far you've come. Be kind to yourself today, okay?",
        "clinical": "Patient reports sleep-onset insomnia with rumination on past events (3AM intrusive recall). Mild depressive affect. No SI/self-harm. Recommend sleep hygiene protocol; consider early-morning light exposure; monitor mood trajectory.",
    },
    {
        "content": "Small win: I journaled even though I didn't want to. Took a shower, made tea, wrote three sentences. That's it. That's the whole win. And honestly it felt like enough.",
        "emotions": "proud, calm, content",
        "patient": "A win is a win and that one counts BIG. Three sentences when your brain was saying 'nah'? That's literally how it's done. Shower, tea, a page written — honestly that's a perfect score today.",
        "clinical": "Patient demonstrates behavioral activation: completed self-care sequence despite low motivation. Reports subjective pride. Positive reinforcement indicated. Maintain current treatment plan.",
    },
    {
        "content": "Bad day. Panic hit me at the supermarket checkout. Everything went loud and I just left my basket and walked out. Felt like everyone was watching. I'm so tired of feeling broken.",
        "emotions": "panicked, embarrassed, frustrated",
        "patient": "Oh hey, first things first — nothing to be embarrassed about, okay? Panic attacks are awful, and you handled it the best you could in that moment by getting yourself out. You're not broken, you're just going through a rough patch. We've got this, one checkout at a time.",
        "clinical": "Patient experienced situational panic attack (supermarket, agoraphobic pattern). Reports shame and fatigue with feeling 'broken.' Risk assessment: no suicidality; elevated distress. Consider in-vivo exposure hierarchy + grounding techniques. Validate and normalize.",
    },
    {
        "content": "Talked to mom on the phone. She doesn't fully get what I'm going through, but she said 'I love you' at the end and I cried a little. It meant more than she knows.",
        "emotions": "bittersweet, loved, grateful",
        "patient": "Okay that hit right in the feels, I can tell. A simple 'I love you' from mom is pure magic, even when they don't fully get what we're going through. And hey, crying a little means you actually felt it — that's a good thing. Love that for you.",
        "clinical": "Patient reports meaningful interpersonal connection with family member. Crying with perceived warmth noted as therapeutic (positive affectivity). Social support network strengthening. Good prognostic indicator.",
    },
    {
        "content": "Meditation is getting less awkward. Did ten minutes and only got distracted seven times instead of forty. My mind is slowly learning to sit still.",
        "emotions": "calm, amused, hopeful",
        "patient": "Haha, 7 distractions instead of 40 is honestly a HUGE upgrade. Your brain is literally learning to chill. Ten minutes of sitting still is no joke either, so keep that streak going!",
        "clinical": "Patient reports improved meditation adherence and reduced cognitive drift. Humor observed. Mindfulness skills consolidating. Reduced baseline anxiety. Continue practice, consider gradual dose increase.",
    },
    {
        "content": "Grey day. Didn't want to get out of bed, but I did, and I ate breakfast and even did a tiny bit of work. It felt like moving through cement. But I moved.",
        "emotions": "sad, tired, resilient",
        "patient": "That sounds heavy, and honestly I'm proud of you for pushing through anyway. Getting out of bed and eating breakfast on a day like that is a REAL win, cement or no cement. You did good today.",
        "clinical": "Patient reports anhedonia and psychomotor slowing with effortful completion of ADLs. Depressive symptoms present but no hopelessness/ideation. Behavioral activation partially effective. Monitor for trajectory; consider scheduling pleasant activity.",
    },
    {
        "content": "One week since my last real panic attack. I put it on my calendar and stared at it for a while. It's just one week. But it's MINE.",
        "emotions": "proud, hopeful, strong",
        "patient": "ONE WEEK?! Okay that's genuinely huge. You should be so, so proud of yourself. That's not just a week on the calendar — that's proof that all the work you're putting in is actually paying off. Soak it in!",
        "clinical": "Patient reports 7-day panic-free interval, first sustained period since symptom onset. Marked improvement in self-efficacy and mood. Treatment gains consolidating. Consider transitioning to maintenance phase.",
    },
    {
        "content": "Made a list of things I'm grateful for. It felt stupid at first but I found fifteen things and that surprised me. My therapist is going to love this.",
        "emotions": "grateful, content, amused",
        "patient": "FIFTEEN things?! And you thought it was stupid at first — look at you, catching all the good stuff. Dr. Cel is definitely going to love this one. Honestly, this made me smile for you.",
        "clinical": "Patient independently applied gratitude intervention (15 items). Positive framing, improved self-appraisal, humor re: therapeutic relationship. Continued progress. Reinforce autonomous coping skill use.",
    },
    {
        "content": "Booked my follow-up for next week. Nervous but also... ready. It's the first time I've looked forward to a session instead of dreading it.",
        "emotions": "anxious, hopeful, brave",
        "patient": "Nervous AND ready — honestly that's the perfect combo. It's kind of beautiful that you're looking forward to a session now instead of dreading it; that means you've built something real there. You've got this!",
        "clinical": "Patient proactively scheduled follow-up; reports anticipatory readiness rather than avoidance. Improved treatment engagement and attendance self-efficacy. Excellent prognostic indicators overall.",
    },
]

for i, j in enumerate(journals):
    ts = (now - timedelta(days=len(journals) - 1 - i, hours=random.randint(8, 21))).isoformat()
    probs = {emo.strip(): round(random.uniform(0.3, 0.9), 3) for emo in j["emotions"].split(",")}
    db.add(
        JournalEntry(
            patient_username="alaya",
            raw_content=j["content"],
            summary=j["patient"],
            clinical_summary=j["clinical"],
            ai_source=("ollama" if i % 3 == 0 else "groq"),
            emotions=j["emotions"],
            emotion_probabilities=json.dumps(probs),
            timestamp=ts,
            created_at=ts,
            version=1,
        )
    )
db.commit()
print(f"  {len(journals)} journals seeded (patient + clinical summaries)")

# ── 4. MOODS ──────────────────────────────────────────────────
mood_labels = [
    ("okay", "\U0001f610"),
    ("anxious", "\U0001f62c"),
    ("good", "\U0001f60a"),
    ("tired", "\U0001f634"),
    ("okay", "\U0001f610"),
    ("great", "\U0001f929"),
    ("sad", "\U0001f641"),
    ("okay", "\U0001f610"),
    ("good", "\U0001f60a"),
    ("hopeful", "\U0001f60c"),
    ("good", "\U0001f60a"),
    ("great", "\U0001f929"),
    ("okay", "\U0001f610"),
    ("proud", "\U0001f4aa"),
]
for i, (label, emoji) in enumerate(mood_labels):
    d = (now - timedelta(days=13 - i)).strftime("%Y-%m-%d")
    ts = (now - timedelta(days=13 - i, hours=random.randint(8, 20))).isoformat()
    db.add(MoodLog(patient_username="alaya", date=d, emoji=emoji, label=label, timestamp=ts))
db.commit()
print(f"  {len(mood_labels)} mood logs")

# ── 5. RING SENSOR DATA ───────────────────────────────────────
for i in range(10):
    ts = (now - timedelta(days=9 - i, hours=random.randint(1, 6))).isoformat()
    db.add(
        RingSensorLog(
            patient_username="alaya",
            device_id="ring_alaya",
            bpm=random.randint(58, 86),
            stress=random.randint(12, 60),
            sleep_hours=round(random.uniform(5.2, 8.6), 1),
            spo2=random.randint(95, 99),
            hrv=random.randint(24, 68),
            logged_at=ts,
        )
    )
db.commit()
print("  10 ring sensor logs")


# ── 6. BOOKINGS ───────────────────────────────────────────────
def days_from_now(d):
    return (now + timedelta(days=d)).strftime("%Y-%m-%d")


bookings = [
    {
        "date": days_from_now(-6),
        "time": "10:00",
        "session_type": "Follow-up",
        "status": "Completed",
        "explanation": "Review of weekly progress",
        "contact": "alaya@sentinel.demo",
    },
    {
        "date": days_from_now(-1),
        "time": "10:00",
        "session_type": "Therapy",
        "status": "Approved",
        "explanation": "Continuing CBT work on anxiety",
        "contact": "alaya@sentinel.demo",
    },
    {
        "date": days_from_now(3),
        "time": "11:00",
        "session_type": "Therapy",
        "status": "Pending",
        "explanation": "Follow-up after good week; want to plan next steps",
        "contact": "alaya@sentinel.demo",
    },
]
for b in bookings:
    db.add(
        Booking(
            patient_username="alaya",
            psychologist_username="cel",
            date=b["date"],
            time=b["time"],
            session_type=b["session_type"],
            status=b["status"],
            contact=b["contact"],
            explanation=b["explanation"],
            created_at=now.isoformat(),
        )
    )
db.commit()
print("  3 bookings (completed / approved / pending)")

# ── 7. FOLLOWUP TASKS ─────────────────────────────────────────
followups = [
    {"title": "Daily Mood Check", "desc": "Log your mood every morning before 10 AM.", "status": "active", "days": -2},
    {
        "title": "Gratitude List",
        "desc": "Write down 3 things you are grateful for tonight.",
        "status": "active",
        "days": -1,
    },
    {
        "title": "Grounding Practice",
        "desc": "Try the 5-4-3-2-1 grounding exercise during a stressful moment.",
        "status": "active",
        "days": 0,
    },
    {
        "title": "Morning Walk",
        "desc": "Walk by the lake for at least 15 minutes.",
        "status": "completed",
        "days": -4,
        "grade": "Excellent",
    },
    {
        "title": "Meditation Session",
        "desc": "10 minutes of guided meditation, 3 times this week.",
        "status": "completed",
        "days": -8,
        "grade": "Good",
    },
]
for f in followups:
    db.add(
        FollowupTask(
            id=str(uuid.uuid4()),
            patient_username="alaya",
            psychologist_username="cel",
            title=f["title"],
            description=f["desc"],
            status=f["status"],
            grade=f.get("grade", ""),
            assigned_at=(now + timedelta(days=f["days"])).isoformat(),
            completed_at=(now + timedelta(days=f["days"], hours=5)).isoformat() if f["status"] == "completed" else "",
        )
    )
db.commit()
print("  5 follow-up tasks (3 active, 2 completed with grades)")

# ── 8. CLINICAL NOTES ─────────────────────────────────────────
clinical_notes = [
    {
        "ts": days_from_now(-6),
        "notes": "Patient presented with mild anxiety symptoms. Reviewed weekly journal; noted improvement in routine adherence. Provided validation and encouraged continued behavioral activation.",
        "synth": "Session 1: Patient engaged, affect congruent with reported improvement. Cognitive work initiated on catastrophizing pattern. Home exercise: gratitude journaling. Plan: monitor panic-free interval.",
    },
    {
        "ts": days_from_now(-1),
        "notes": "Good session. Patient reported first panic-free week and completed gratitude list independently. Reinforced gains, discussed next-stage coping strategies.",
        "synth": "Session 2: Notable progress — sustained symptom reduction, autonomous use of coping skills. Self-efficacy improving. Continue maintenance-focused CBT; next review in one week.",
    },
]
for n in clinical_notes:
    db.add(
        ClinicalNote(
            psychologist_username="cel",
            patient_username="alaya",
            raw_notes=n["notes"],
            ai_synthesis=n["synth"],
            timestamp=n["ts"],
        )
    )
db.commit()
print("  2 clinical notes")

# ── 9. PSYCH JOURNAL (Dr. Cel's notes) ────────────────────────
psych_journals = [
    (
        "Alaya made real progress today. The supermarket episode shook her, but she turned it into motivation. Watch for avoidance behavior developing around grocery settings.",
        "Session reflection: notable resilience; plan graded exposure for next week.",
        "groq",
    ),
    (
        "She booked her follow-up without prompting. That's a shift in treatment alliance — from compliance to ownership. Very encouraging.",
        "Marker: patient-initiated care. Transitioning to maintenance phase.",
        "ollama",
    ),
]
for content, summary, source in psych_journals:
    db.add(
        PsychJournalEntry(
            psychologist_username="cel",
            raw_content=content,
            summary=summary,
            ai_source=source,
            emotions="reflective, encouraged",
            timestamp=(now - timedelta(days=random.randint(0, 4), hours=random.randint(9, 19))).isoformat(),
        )
    )
db.commit()
print("  2 psych journal entries")

# ── 10. RISK ASSESSMENTS ──────────────────────────────────────
journal_rows = db.query(JournalEntry).filter(JournalEntry.patient_username == "alaya").all()
for jr in journal_rows[1:4]:
    db.add(
        RiskAssessment(
            journal_id=jr.id,
            patient_username="alaya",
            risk_score=random.choice([15, 20, 10]),
            triggered=0,
            confidence=round(random.uniform(0.7, 0.9), 2),
            explanation="Somatic anxiety indicators present; no suicidality markers detected. Moderate monitor flag.",
            algorithm_version="1.0.0",
            created_at=jr.timestamp,
        )
    )
db.commit()
print("  3 risk assessments")

# ── 11. NOTIFICATIONS ─────────────────────────────────────────
notifications = [
    {
        "title": "Welcome to Sentinel",
        "message": "Hi Alaya, your account is ready. Start by logging your mood or writing a journal entry.",
        "ntype": "system",
        "days": 13,
    },
    {
        "title": "Booking Approved",
        "message": "Dr. Cel accepted your therapy session for tomorrow at 10:00.",
        "ntype": "info",
        "days": 1,
    },
    {
        "title": "Booking Pending",
        "message": "Your follow-up request for next week is waiting for approval.",
        "ntype": "reminder",
        "days": 0,
    },
    {
        "title": "Journal Streak",
        "message": "You've been journaling regularly. Keep it up — consistency is progress.",
        "ntype": "system",
        "days": 2,
    },
]
for n in notifications:
    db.add(
        Notification(
            patient_username="alaya",
            title=n["title"],
            message=n["message"],
            notification_type=n["ntype"],
            sent_at=(now - timedelta(days=n["days"])).isoformat(),
        )
    )
db.commit()
print("  4 notifications")

# ── 12. CRISIS STATE RESET ────────────────────────────────────
cs = db.query(CrisisState).first()
if cs:
    cs.active = 0
    cs.patient_username = ""
else:
    db.add(CrisisState(active=0))
db.commit()
print("  crisis state reset")

print()
print("=== DONE ===")
print("  Login:")
print("    Psych:   cel  / 1234")
print("    Patient: alaya / 4321")
db.close()
