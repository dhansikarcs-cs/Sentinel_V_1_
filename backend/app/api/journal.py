from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.journal import JournalEntry
from app.schemas.journal import JournalCreate, JournalResponse
from app.services.ai_service import summarize_journal

router = APIRouter(prefix="/journal", tags=["journal"])


@router.post("", response_model=JournalResponse)
def create_journal(entry: JournalCreate, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    ai_result = summarize_journal(entry.raw_content)
    journal = JournalEntry(
        patient_username=user.username,
        raw_content=entry.raw_content,
        summary=ai_result.get("summary", entry.raw_content[:200]),
        ai_source=ai_result.get("ai_source", "rule"),
        emotions=ai_result.get("emotions", ""),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    db.add(journal)
    db.commit()
    db.refresh(journal)
    return journal


@router.get("", response_model=list[JournalResponse])
def get_journals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    journals = db.query(JournalEntry).filter(JournalEntry.patient_username == user.username).order_by(JournalEntry.timestamp.desc()).all()
    return journals


@router.get("/{username}", response_model=list[JournalResponse])
def get_patient_journals(username: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    journals = db.query(JournalEntry).filter(JournalEntry.patient_username == username).order_by(JournalEntry.timestamp.desc()).all()
    return journals


@router.get("/{username}/summaries")
def get_patient_summaries(username: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    entries = db.query(JournalEntry).filter(JournalEntry.patient_username == username).order_by(JournalEntry.timestamp.desc()).limit(20).all()
    return [
        {"id": e.id, "summary": e.summary, "ai_source": e.ai_source, "emotions": e.emotions, "timestamp": e.timestamp}
        for e in entries
    ]
