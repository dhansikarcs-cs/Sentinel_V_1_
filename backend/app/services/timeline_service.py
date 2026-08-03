"""Change-metrics and timeline-event assembly for a single patient.

Constitution #6 (single owner): both the /timeline API and the
/patients/{username}/overview composite consume this one build instead of
re-implementing the same queries and thresholds.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.crisis import CrisisLog
from app.models.followup import FollowupTask
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.schemas.timeline import ChangeMetrics, TimelineEvent

_mood_val = {"great": 5, "good": 4, "okay": 3, "bad": 2, "awful": 1, "terrible": 0}


def compute_change_metrics(username: str, db: Session) -> ChangeMetrics:
    now = datetime.now()
    cutoff_14 = (now - timedelta(days=14)).isoformat()
    cutoff_7 = (now - timedelta(days=7)).isoformat()

    moods = db.query(MoodLog).filter(MoodLog.patient_username == username, MoodLog.timestamp >= cutoff_14).all()

    current = [m for m in moods if m.timestamp >= cutoff_7]
    previous = [m for m in moods if cutoff_14 <= m.timestamp < cutoff_7]

    def avg(ms):
        vals = [v for v in [_mood_val.get(m.label) for m in ms] if v is not None]
        return sum(vals) / len(vals) if vals else None

    curr_avg = avg(current)
    prev_avg = avg(previous)

    journals_7 = (
        db.query(JournalEntry)
        .filter(JournalEntry.patient_username == username, JournalEntry.timestamp >= cutoff_7)
        .count()
    )
    journals_14 = (
        db.query(JournalEntry)
        .filter(JournalEntry.patient_username == username, JournalEntry.timestamp >= cutoff_14)
        .count()
    )

    if curr_avg is not None and prev_avg is not None and prev_avg > 0:
        pct = round((curr_avg - prev_avg) / prev_avg * 100, 1)
    else:
        pct = None

    if curr_avg is not None and prev_avg is not None:
        trend = "improving" if curr_avg > prev_avg + 0.25 else "declining" if curr_avg < prev_avg - 0.25 else "stable"
    else:
        trend = "insufficient_data"

    eng = (
        "increasing"
        if journals_7 > max(1, journals_14 / 2)
        else "declining"
        if journals_7 < journals_14 / 4 and journals_14 > 0
        else "stable"
        if journals_14 > 0
        else "none"
    )

    return ChangeMetrics(
        current_mood_avg=curr_avg,
        previous_mood_avg=prev_avg,
        mood_trend=trend,
        mood_change_pct=pct,
        journal_count_7=journals_7,
        journal_count_14=journals_14,
        engagement_trend=eng,
    )


def build_timeline_events(username: str, days: int, db: Session) -> list[TimelineEvent]:
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    events = []

    for m in db.query(MoodLog).filter(MoodLog.patient_username == username, MoodLog.timestamp >= cutoff).all():
        events.append(
            TimelineEvent(type="mood", timestamp=m.timestamp, data={"date": m.date, "emoji": m.emoji, "label": m.label})
        )

    for j in (
        db.query(JournalEntry).filter(JournalEntry.patient_username == username, JournalEntry.timestamp >= cutoff).all()
    ):
        events.append(
            TimelineEvent(
                type="journal",
                timestamp=j.timestamp,
                data={"title": j.summary[:60] if j.summary else "Journal Entry", "emotions": j.emotions or ""},
            )
        )

    for f in (
        db.query(FollowupTask)
        .filter(FollowupTask.patient_username == username, FollowupTask.assigned_at >= cutoff)
        .all()
    ):
        events.append(
            TimelineEvent(
                type="followup", timestamp=f.assigned_at, data={"title": f.title, "status": f.status, "grade": f.grade}
            )
        )

    for c in db.query(CrisisLog).filter(CrisisLog.patient == username, CrisisLog.timestamp >= cutoff).all():
        events.append(
            TimelineEvent(type="crisis", timestamp=c.timestamp, data={"event": c.event, "details": c.details or ""})
        )

    events.sort(key=lambda e: e.timestamp, reverse=True)
    return events
