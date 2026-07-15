from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.followup import FollowupTask
from app.models.crisis import CrisisLog
from app.schemas.timeline import TimelineResponse, TimelineEvent, ChangeMetrics

router = APIRouter(prefix="/timeline", tags=["timeline"])


_mood_val = {"great": 5, "good": 4, "okay": 3, "bad": 2, "awful": 1, "terrible": 0}


def _compute_change_metrics(username: str, db: Session) -> ChangeMetrics:
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

    journals_7 = db.query(JournalEntry).filter(JournalEntry.patient_username == username, JournalEntry.timestamp >= cutoff_7).count()
    journals_14 = db.query(JournalEntry).filter(JournalEntry.patient_username == username, JournalEntry.timestamp >= cutoff_14).count()

    if curr_avg is not None and prev_avg is not None and prev_avg > 0:
        pct = round((curr_avg - prev_avg) / prev_avg * 100, 1)
    else:
        pct = None

    if curr_avg is not None and prev_avg is not None:
        trend = "improving" if curr_avg > prev_avg + 0.25 else "declining" if curr_avg < prev_avg - 0.25 else "stable"
    else:
        trend = "insufficient_data"

    eng = "increasing" if journals_7 > max(1, journals_14 / 2) else "declining" if journals_7 < journals_14 / 4 and journals_14 > 0 else "stable" if journals_14 > 0 else "none"

    return ChangeMetrics(
        current_mood_avg=curr_avg,
        previous_mood_avg=prev_avg,
        mood_trend=trend,
        mood_change_pct=pct,
        journal_count_7=journals_7,
        journal_count_14=journals_14,
        engagement_trend=eng,
    )


@router.get("/{username}", response_model=TimelineResponse)
def get_timeline(username: str, days: int = Query(30, ge=1, le=90), user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    events = []

    for m in db.query(MoodLog).filter(MoodLog.patient_username == username, MoodLog.timestamp >= cutoff).all():
        events.append(TimelineEvent(type="mood", timestamp=m.timestamp, data={"date": m.date, "emoji": m.emoji, "label": m.label}))

    for j in db.query(JournalEntry).filter(JournalEntry.patient_username == username, JournalEntry.timestamp >= cutoff).all():
        events.append(TimelineEvent(type="journal", timestamp=j.timestamp, data={"title": j.summary[:60] if j.summary else "Journal Entry", "emotions": j.emotions or ""}))

    for f in db.query(FollowupTask).filter(FollowupTask.patient_username == username, FollowupTask.assigned_at >= cutoff).all():
        events.append(TimelineEvent(type="followup", timestamp=f.assigned_at, data={"title": f.title, "status": f.status, "grade": f.grade}))

    for c in db.query(CrisisLog).filter(CrisisLog.patient == username, CrisisLog.timestamp >= cutoff).all():
        events.append(TimelineEvent(type="crisis", timestamp=c.timestamp, data={"event": c.event, "details": c.details or ""}))

    events.sort(key=lambda e: e.timestamp, reverse=True)
    metrics = _compute_change_metrics(username, db)

    return TimelineResponse(events=events, metrics=metrics)


@router.get("/{username}/metrics")
def get_change_metrics(username: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    return _compute_change_metrics(username, db)
