from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.psych_journal import PsychJournalEntry
from app.models.user import User
from app.schemas.psych_journal import PsychJournalCreate, PsychJournalResponse
from app.services.ai_service import summarize_journal
from app.services.audit import log_audit

router = APIRouter(prefix="/psych-journal", tags=["psych-journal"])


@router.post("", response_model=PsychJournalResponse)
def create_psych_journal(
    entry: PsychJournalCreate, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    result = summarize_journal(entry.raw_content, mode="patient")
    journal = PsychJournalEntry(
        psychologist_username=user.username,
        raw_content=entry.raw_content,
        summary=result.get("summary", entry.raw_content[:200]),
        ai_source=result.get("ai_source", "rule"),
        emotions=result.get("emotions", ""),
        timestamp=datetime.now(UTC).isoformat(),
    )
    db.add(journal)
    db.commit()
    db.refresh(journal)
    log_audit(
        "psych_journal_created",
        user=user.username,
        role=user.role,
        severity="INFO",
        status="success",
        resource=str(journal.id),
        db=db,
    )
    return journal


@router.get("", response_model=list[PsychJournalResponse])
def get_psych_journals(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    journals = (
        db.query(PsychJournalEntry)
        .filter(PsychJournalEntry.psychologist_username == user.username)
        .order_by(PsychJournalEntry.timestamp.desc())
        .all()
    )
    return journals
