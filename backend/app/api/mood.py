from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.mood import MoodLog
from app.schemas.mood import MoodCreate, MoodResponse

router = APIRouter(prefix="/mood", tags=["mood"])


@router.post("", response_model=MoodResponse)
def log_mood(entry: MoodCreate, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    mood = MoodLog(
        patient_username=user.username,
        date=entry.date,
        emoji=entry.emoji,
        label=entry.label,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    db.add(mood)
    db.commit()
    db.refresh(mood)
    return mood


@router.get("/today/check")
def check_today_mood(user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    from datetime import date
    today = date.today().isoformat()
    existing = db.query(MoodLog).filter(MoodLog.patient_username == user.username, MoodLog.date == today).first()
    return {"logged": existing is not None}


@router.get("", response_model=list[MoodResponse])
def get_moods(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    moods = db.query(MoodLog).filter(MoodLog.patient_username == user.username).order_by(MoodLog.timestamp.desc()).limit(30).all()
    return moods


@router.get("/{username}", response_model=list[MoodResponse])
def get_patient_moods(username: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    moods = db.query(MoodLog).filter(MoodLog.patient_username == username).order_by(MoodLog.timestamp.desc()).limit(30).all()
    return moods
