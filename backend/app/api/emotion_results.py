from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.emotion_result import EmotionResult
from app.schemas.emotion_result import EmotionResultResponse

router = APIRouter(prefix="/emotion-results", tags=["emotion_results"])


@router.get("/journal/{journal_id}", response_model=EmotionResultResponse)
def get_emotion_result_by_journal(journal_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = db.query(EmotionResult).filter(EmotionResult.journal_id == journal_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Emotion result not found")
    return result


@router.get("/patient/{username}", response_model=list[EmotionResultResponse])
def get_emotion_results_for_patient(username: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    return (
        db.query(EmotionResult)
        .filter(EmotionResult.patient_username == username)
        .order_by(EmotionResult.created_at.desc())
        .limit(50)
        .all()
    )
