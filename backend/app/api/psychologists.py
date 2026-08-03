from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.journal import JournalEntry
from app.models.clinical_note import ClinicalNote
from app.repositories import PatientRepository
from app.events import get_event_bus
from app.services.audit import log_audit

router = APIRouter(prefix="/psychologists", tags=["psychologists"])


@router.get("/patients")
def get_assigned_patients(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    repo = PatientRepository(db)
    patients = repo.get_assigned_patients(user.username)
    return [
        {
            "username": p.username,
            "name": p.name,
            "age": p.age,
            "occupation": p.occupation,
            "clinic": p.clinic_code or "",
            "onboarding_step": p.onboarding_step or 0,
        }
        for p in patients
    ]


@router.get("/available")
def get_available_psychologists(clinic: str = "", db: Session = Depends(get_db)):
    repo = PatientRepository(db)
    return [{"username": p.username, "name": p.name} for p in repo.get_psychologists(clinic)]


@router.post("/notes")
def save_clinical_note(patient_username: str, raw_notes: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    note = ClinicalNote(
        psychologist_username=user.username,
        patient_username=patient_username,
        raw_notes=raw_notes,
        ai_synthesis=raw_notes,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    db.add(note)
    db.commit()
    get_event_bus().emit("clinical_note:saved", psych=user.username, patient=patient_username)
    return {"message": "Saved"}


@router.get("/notes")
def get_clinical_notes(patient: str = "", user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    query = db.query(ClinicalNote).filter(ClinicalNote.psychologist_username == user.username)
    if patient:
        query = query.filter(ClinicalNote.patient_username == patient)
    notes = query.order_by(ClinicalNote.timestamp.desc()).limit(50).all()
    return [
        {
            "id": n.id,
            "patient": n.patient_username,
            "ai_synthesis": n.ai_synthesis,
            "timestamp": n.timestamp,
        }
        for n in notes
    ]
