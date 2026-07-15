from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.followup import FollowupTask
from app.models.ring import RingSensorLog

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/me")
def get_me(user: User = Depends(require_role("patient", "psychologist"))):
    return {
        "username": user.username,
        "name": user.name,
        "role": user.role,
        "clinic": user.clinic_code or "",
        "contact_info": user.contact_info or "",
        "trusted_contact": user.trusted_contact or "",
        "assigned_psych": user.assigned_psych or "",
        "onboarding_step": user.onboarding_step or 0,
    }


@router.get("/{username}/profile")
def get_patient_profile(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return {"error": "Not found"}
    return {
        "username": user.username,
        "name": user.name,
        "role": user.role,
        "clinic": user.clinic_code or "",
    }


@router.get("/{username}/summary")
def get_patient_summary(username: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    journals = db.query(JournalEntry).filter(JournalEntry.patient_username == username).order_by(JournalEntry.timestamp.desc()).limit(10).all()
    moods = db.query(MoodLog).filter(MoodLog.patient_username == username).order_by(MoodLog.timestamp.desc()).limit(7).all()
    ring_data = db.query(RingSensorLog).filter(RingSensorLog.patient_username == username).order_by(RingSensorLog.logged_at.desc()).first()
    followups = db.query(FollowupTask).filter(FollowupTask.patient_username == username).order_by(FollowupTask.assigned_at.desc()).limit(10).all()

    return {
        "journals": [{"id": j.id, "summary": j.summary or "", "emotions": j.emotions or "", "ai_source": j.ai_source or "", "timestamp": j.timestamp} for j in journals],
        "moods": [{"date": m.date, "emoji": m.emoji, "label": m.label, "timestamp": m.timestamp} for m in moods],
        "ring": {"bpm": ring_data.bpm if ring_data else 0, "stress": ring_data.stress if ring_data else 0, "sleep": ring_data.sleep_hours if ring_data else 0, "spo2": ring_data.spo2 if ring_data else 0} if ring_data else None,
        "followups": [{"id": f.id, "title": f.title, "status": f.status, "grade": f.grade} for f in followups],
    }


class ContactUpdate(BaseModel):
    contact_info: str = ""
    trusted_contact: str = ""


@router.put("/me/contact")
def update_contact(update: ContactUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        db_user.contact_info = update.contact_info
        if update.trusted_contact:
            db_user.trusted_contact = update.trusted_contact
        db.commit()
    return {"message": "Updated"}
