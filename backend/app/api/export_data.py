import csv
import io
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.followup import FollowupTask
from app.models.crisis import CrisisLog
from app.services.audit import log_audit

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/journal-summaries")
def export_journal_summaries(user: User = Depends(require_role("psychologist")), days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    patients = db.query(User).filter(User.assigned_psych == user.username, User.role == "patient").all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Patient", "Date", "Entry", "AI Summary", "Emotions", "AI Source", "HMAC"])

    for p in patients:
        entries = db.query(JournalEntry).filter(
            JournalEntry.patient_username == p.username,
            JournalEntry.timestamp >= cutoff
        ).order_by(JournalEntry.timestamp).all()
        for e in entries:
            writer.writerow([p.username, e.timestamp[:10] if e.timestamp else "", (e.raw_content or "")[:200], e.summary or "", e.emotions or "", e.ai_source or "", e.hmac or ""])

    output.seek(0)
    log_audit("export_journal_summaries", user=user.username, role=user.role, severity="INFO", status="success", details=f"days={days}, patients={len(patients)}", db=db)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=sentinel_journal_summaries.csv"})


@router.get("/clinical-notes")
def export_clinical_notes(user: User = Depends(require_role("psychologist")), days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    from app.models.clinical_note import ClinicalNote
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Patient", "Date", "Raw Notes", "AI Synthesis"])

    notes = db.query(ClinicalNote).filter(
        ClinicalNote.psychologist_username == user.username,
        ClinicalNote.timestamp >= cutoff
    ).order_by(ClinicalNote.timestamp).all()

    for n in notes:
        writer.writerow([n.patient_username, n.timestamp[:10] if n.timestamp else "", (n.raw_notes or "")[:200], n.ai_synthesis or ""])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=sentinel_clinical_notes.csv"})


@router.get("/patient-data")
def export_patient_data(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    patients = db.query(User).filter(User.assigned_psych == user.username, User.role == "patient").all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Patient", "Name", "Age", "Occupation", "Clinic", "Assigned Psych", "Onboarding Step", "Registered"])

    for p in patients:
        writer.writerow([p.username, p.name, p.age, p.occupation, p.clinic_code or "", p.assigned_psych or "", p.onboarding_step or 0, (p.created_at or "")[:10]])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=sentinel_patient_data.csv"})
