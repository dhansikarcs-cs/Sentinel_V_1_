import json
from collections import Counter
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.journal import JournalEntry

router = APIRouter(prefix="/emotions", tags=["emotions"])


@router.get("/timeline/{username}")
def get_emotion_timeline(
    username: str,
    days: int = 30,
    user: User = Depends(require_role("psychologist")),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    entries = (
        db.query(JournalEntry)
        .filter(
            JournalEntry.patient_username == username,
            JournalEntry.timestamp >= cutoff,
            JournalEntry.emotion_probabilities != "",
        )
        .order_by(JournalEntry.timestamp.asc())
        .all()
    )
    timeline = []
    emotion_heatmap: dict[str, list[dict]] = {}
    for e in entries:
        probs = {}
        if e.emotion_probabilities:
            try:
                probs = json.loads(e.emotion_probabilities)
            except (json.JSONDecodeError, TypeError):
                probs = {}
        point = {
            "journal_id": e.id,
            "timestamp": e.timestamp,
            "emotions": e.emotions,
            "emotion_probabilities": probs,
        }
        timeline.append(point)
        for emo, prob in probs.items():
            if prob > 0:
                emotion_heatmap.setdefault(emo, []).append({"timestamp": e.timestamp, "probability": prob})

    emotion_summary = {}
    for emo, points in emotion_heatmap.items():
        if points:
            avg = sum(p["probability"] for p in points) / len(points)
            max_p = max(points, key=lambda x: x["probability"])
            emotion_summary[emo] = {
                "average": round(avg, 3),
                "max": round(max_p["probability"], 3),
                "max_at": max_p["timestamp"],
                "count": len(points),
            }

    return {
        "patient_username": username,
        "days": days,
        "entries_count": len(timeline),
        "timeline": timeline,
        "emotion_summary": emotion_summary,
    }


@router.get("/summary/{username}")
def get_emotion_summary(
    username: str,
    days: int = 30,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    entries = (
        db.query(JournalEntry)
        .filter(
            JournalEntry.patient_username == username,
            JournalEntry.timestamp >= cutoff,
        )
        .order_by(JournalEntry.timestamp.asc())
        .all()
    )
    emotion_counts: Counter = Counter()
    total = 0
    for e in entries:
        if e.emotions:
            for emo in e.emotions.split(","):
                emo = emo.strip()
                if emo:
                    emotion_counts[emo] += 1
                    total += 1
    dominant = emotion_counts.most_common(5)
    return {
        "patient_username": username,
        "days": days,
        "total_entries": len(entries),
        "top_emotions": [{"emotion": e, "count": c, "percentage": round(c / total * 100, 1) if total else 0} for e, c in dominant],
    }
