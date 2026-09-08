"""Add a dedicated HRV experiment patient with a long depressive timeline.

Non-destructive: only adds rows for a NEW patient (hrvdemo). It does NOT
clear or touch any existing data, so camtest1 / alaya / cel / demo_psych
remain untouched. Re-run is safe (skips if the patient already exists).

Seeds, going back ~6 weeks:
  - account (role=patient) hrvdemo / Test!Pass123
  - long depressive journal timeline (raw entries + patient/clinical summaries)
  - declining mood logs
  - prior physiological history (RingSensorLog + PhysiologicalSignal baseline)
  - a couple of preceding risk assessments so the overview has history

All timestamps are backdated so the overview "changes" / trend logic sees a
real longitudinal arc instead of one spike today.
"""

import os
import sys
from datetime import UTC, datetime, timedelta

sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.journal import JournalEntry  # noqa: E402
from app.models.mood import MoodLog  # noqa: E402
from app.models.physiological_signal import PhysiologicalSignal  # noqa: E402
from app.models.ring import RingSensorLog  # noqa: E402
from app.models.risk_assessment import RiskAssessment  # noqa: E402
from app.models.user import User  # noqa: E402

USERNAME = "hrvdemo"
PASSWORD = "Test!Pass123"
PSYCH = "demo_psych"
now = datetime.now(UTC)

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if db.query(User).filter(User.username == USERNAME).first():
    print(f"patient {USERNAME} already exists — nothing to do (safe re-run)")
    db.close()
    sys.exit(0)


def salt():
    return os.urandom(16).hex()


# ── 1. PSYCHOLOGIST (only if not present) ─────────────────────
if not db.query(User).filter(User.username == PSYCH).first():
    db.add(
        User(
            username=PSYCH,
            password_hash=hash_password("Test!Pass123"),
            name="Dr. Demo Psych",
            role="psychologist",
            clinic_code="DEMO",
            onboarding_step=99,
            contact_info="demo.psych@sentinel.demo",
            encryption_salt=salt(),
            created_at=(now - timedelta(days=90)).isoformat(),
        )
    )
    print(f"  created psych: {PSYCH}")

# ── 2. PATIENT ACCOUNT ────────────────────────────────────────
db.add(
    User(
        username=USERNAME,
        password_hash=hash_password(PASSWORD),
        name="HRV Demo",
        role="patient",
        age=34,
        occupation="Software developer",
        clinic_code="DEMO",
        onboarding_step=99,
        contact_info="hrvdemo@sentinel.demo",
        trusted_contact="demo-trusted@sentinel.demo",
        assigned_psych=PSYCH,
        encryption_salt=salt(),
        created_at=(now - timedelta(days=80)).isoformat(),
    )
)
db.commit()
print(f"  created patient: {USERNAME} / {PASSWORD}")

# ── 3. LONG DEPRESSIVE JOURNAL TIMELINE (6 weeks) ─────────────
# (day_delta, patient content, clinical summary)  day_delta=0 is most recent
TIMELINE = [
    (
        1,
        "Woke up with that familiar heaviness again. Didn't sleep well. Everything feels like it takes so much effort.",
        "Patient reports sleep-onset difficulty with early waking; anhedonia with effortful ADLs.",
    ),
    (
        3,
        "Couldn't get out of bed until noon. Canceled plans again. feeling worthless and guilty about everything.",
        "Psychomotor slowing; social withdrawal; endorsements of worthlessness and guilt.",
    ),
    (
        5,
        "Tried to go for a walk like my therapist suggested. Felt anxious the whole time, heart racing. Gave up halfway.",
        "Attempted behavioral activation; anxiety symptoms during exposure; partial completion.",
    ),
    (
        7,
        "Bad day. Cried for hours without really knowing why. Nothing brings me joy anymore. Am I ever going to feel normal?",
        "Prominent anhedonia; tearfulness; hopelessness; passive wish for change in state.",
    ),
    (
        9,
        "Managed to shower and eat today. Small win but it took everything I had. Proud but also exhausted.",
        "Demonstrates behavioral activation; fluctuating energy and low mood throughout day.",
    ),
    (
        11,
        "Work feels impossible. Sending one email took an hour. I keep making excuses because getting anything done is overwhelming.",
        "Cognitive fatigue and impaired concentration; occupational functioning affected.",
    ),
    (
        13,
        "Woke up at 4am replaying old mistakes over and over. Ruminating again. Can't stop the noise in my head.",
        "Early-morning awakening complicated by rumination; insomnia symptom endorsement.",
    ),
    (
        15,
        "Therapist says my progress is real but I don't feel it. I don't trust the good moments. Waiting for the other shoe to drop.",
        "Cognitive distortion (discounting positives); affective non-responsiveness to observed progress.",
    ),
    (
        17,
        "Stayed in bed most of the weekend. Ignored calls. Felt like a burden to everyone around me.",
        "Social withdrawal; perceived burdensomeness; low activity level through weekend.",
    ),
    (
        19,
        "I keep reminding myself this is an illness, not a character flaw. Some days that actually helps now.",
        "Improved cognitive reframing; partial therapeutic insight.",
    ),
    (
        21,
        "Heart has been pounding all week even when I'm just sitting. Doctor said stress but it feels physical sometimes.",
        "Somatic complaints consistent with anxiety; health-related worry; physiological activation.",
    ),
    (
        23,
        "Did a full day of work without breaking down. Felt almost normal for an hour this afternoon. Holding onto that.",
        "Meaningful functional improvement; brief period of euthymia; gains holding across day.",
    ),
    (
        25,
        "Hard night. Couldn't stop crying, felt completely alone. Called the helpline and talked to someone — it helped a little.",
        "Acute distress with adaptive help-seeking; crisis hotline utilization; support-seeking behavior.",
    ),
    (
        27,
        "Getting out of bed earlier the last few days. Mood still low but the fog feels a bit thinner.",
        "Gradual behavioral activation gains; mood slowly lifting; sustained sleep improvement.",
    ),
    (
        30,
        "Good day today. Met a friend, laughed, felt present. Grateful to have made it through this week.",
        "Positive affect; social engagement; meaningful interpersonal connection experienced.",
    ),
]

print(f"=== SEEDING {len(TIMELINE)} JOURNAL ENTRIES (6-week depressive arc) ===")
for i, (day_delta, content, clinical) in enumerate(TIMELINE):
    ts = (now - timedelta(days=day_delta, hours=9 + i % 8)).isoformat()
    db.add(
        JournalEntry(
            patient_username=USERNAME,
            raw_content=content,
            summary=("A note to self: " + content[:60]).strip(),
            clinical_summary=clinical,
            ai_source="seeded",
            emotions="sad" if day_delta not in (15, 23, 30) else "mixed",
            emotion_probabilities='{"sad": 0.8, "anxious": 0.15}',
            timestamp=ts,
            created_at=ts,
            updated_at=ts,
            version=1,
        )
    )
db.commit()
print(f"  {len(TIMELINE)} journals seeded")

# ── 4. DECLINING MOODS (same window) ──────────────────────────
MOODS = [
    (2, "😟", "low"),
    (4, "😞", "sad"),
    (6, "😟", "low"),
    (8, "😔", "down"),
    (10, "😞", "sad"),
    (12, "😟", "low"),
    (14, "😞", "sad"),
    (16, "😐", "neutral"),
    (18, "😟", "low"),
    (20, "😞", "sad"),
    (22, "😰", "anxious"),
    (24, "😐", "neutral"),
    (26, "😟", "low"),
    (28, "😊", "okay"),
]
print("=== SEEDING MOODS ===")
for day_delta, emoji, label in MOODS:
    d = (now - timedelta(days=day_delta)).strftime("%Y-%m-%d")
    ts = (now - timedelta(days=day_delta, hours=8)).isoformat()
    db.add(
        MoodLog(
            patient_username=USERNAME,
            date=d,
            emoji=emoji,
            label=label,
            timestamp=ts,
        )
    )
db.commit()
print(f"  {len(MOODS)} mood logs seeded")

# ── 5. PRIOR PHYSIOLOGICAL HISTORY (baseline 72 BPM) ──────────
# Two baseline RingSensorLog rows (>1 so the ring "prev vs latest" logic has
# a prior to compare), plus matching normalized PhysiologicalSignal rows.
print("=== SEEDING PRIOR PHYSIO HISTORY ===")
RING_HISTORY = [
    (21, 72, 38, 6.2, 98.0, 42),  # (day_delta, bpm, stress, sleep, spo2, hrv)
    (14, 74, 41, 6.0, 98.0, 40),
    (7, 78, 48, 5.4, 97.0, 36),
]
for day_delta, bpm, stress, sleep, spo2, hrv in RING_HISTORY:
    ts = (now - timedelta(days=day_delta, hours=6)).isoformat()
    db.add(
        RingSensorLog(
            device_id="camera_ppg",
            patient_username=USERNAME,
            bpm=bpm,
            stress=stress,
            sleep_hours=sleep,
            spo2=spo2,
            hrv=hrv,
            raw_json="{}",
            logged_at=ts,
        )
    )
    db.add(
        PhysiologicalSignal(
            patient_username=USERNAME,
            device_id="camera_ppg_demo",
            vendor="camera_ppg",
            heart_rate=bpm,
            hrv_rmssd=float(hrv),
            stress=stress,
            sleep_hours=float(sleep),
            spo2=float(spo2),
            quality="good",
            confidence=0.7,
            raw_json="{}",
            logged_at=ts,
        )
    )
db.commit()
print(f"  {len(RING_HISTORY)} ring logs + physio signals seeded")

# ── 6. PRIOR RISK ASSESSMENTS (match the low-mood arc) ────────
print("=== SEEDING PRIOR RISK ASSESSMENTS ===")
RISK_HISTORY = [
    (28, 4, 0, 0.6, "Moderate: anhedonia and low engagement; no active crisis indicators."),
    (14, 5, 0, 0.7, "Elevated: sustained low mood, passivity, but no expressed intent or plan."),
]
for day_delta, score, triggered, conf, explanation in RISK_HISTORY:
    ts = (now - timedelta(days=day_delta)).isoformat()
    db.add(
        RiskAssessment(
            journal_id=None,
            emotion_result_id=None,
            sensor_reading_id=None,
            patient_username=USERNAME,
            risk_score=score,
            triggered=triggered,
            confidence=conf,
            explanation=explanation,
            algorithm_version="1.0.0",
            created_at=ts,
        )
    )
db.commit()
print(f"  {len(RISK_HISTORY)} risk assessments seeded")

db.close()
print("\nDone. Patient ready: POST /auth/login as hrvdemo / Test!Pass123")
print("Then push a live higher-BPM reading and call GET /patients/hrvdemo/overview")
print("as the psychologist to watch the derived priorities react.")
