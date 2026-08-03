import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.api_response import ok
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.input_validator import validate_file_upload
from app.events import get_event_bus
from app.models.crisis import CrisisState
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.ring import RingSensorLog
from app.models.risk_assessment import RiskAssessment
from app.models.user import User
from app.repositories import BookingRepository, FollowupRepository, JournalRepository, PatientRepository
from app.services.patient_context import recent_patient_context
from app.services.timeline_service import build_timeline_events, compute_change_metrics

CONSENT_DIR = "data/consent_forms"
os.makedirs(CONSENT_DIR, exist_ok=True)

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/me")
def get_me(user: User = Depends(require_role("patient", "psychologist"))):
    return ok(
        data={
            "username": user.username,
            "name": user.name,
            "role": user.role,
            "clinic": user.clinic_code or "",
            "contact_info": user.contact_info or "",
            "trusted_contact": user.trusted_contact or "",
            "assigned_psych": user.assigned_psych or "",
            "onboarding_step": user.onboarding_step or 0,
        }
    )


@router.get("/{username}/profile")
def get_patient_profile(username: str, db: Session = Depends(get_db)):
    repo = PatientRepository(db)
    user = repo.get_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="Patient not found")
    return ok(
        data={
            "username": user.username,
            "name": user.name,
            "role": user.role,
            "clinic": user.clinic_code or "",
        }
    )


def _owns_or_psych(username: str, user: User) -> bool:
    return user.username == username or user.role == "psychologist"


@router.get("/{username}/summary")
def get_patient_summary(username: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _owns_or_psych(username, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    journal_repo = JournalRepository(db)
    journals = journal_repo.get_by_patient(username, limit=10)
    moods = (
        db.query(MoodLog).filter(MoodLog.patient_username == username).order_by(MoodLog.timestamp.desc()).limit(7).all()
    )
    ring_data = (
        db.query(RingSensorLog)
        .filter(RingSensorLog.patient_username == username)
        .order_by(RingSensorLog.logged_at.desc())
        .first()
    )
    followup_repo = FollowupRepository(db)
    followups = followup_repo.get_for_patient(username)

    return ok(
        data={
            "journals": [
                {
                    "id": j.id,
                    "summary": j.summary or "",
                    "emotions": j.emotions or "",
                    "ai_source": j.ai_source or "",
                    "timestamp": j.timestamp,
                }
                for j in journals
            ],
            "moods": [{"date": m.date, "emoji": m.emoji, "label": m.label, "timestamp": m.timestamp} for m in moods],
            "ring": {
                "bpm": ring_data.bpm if ring_data else 0,
                "stress": ring_data.stress if ring_data else 0,
                "sleep": ring_data.sleep_hours if ring_data else 0,
                "spo2": ring_data.spo2 if ring_data else 0,
            }
            if ring_data
            else None,
            "followups": [{"id": f.id, "title": f.title, "status": f.status, "grade": f.grade} for f in followups],
        }
    )


class ContactUpdate(BaseModel):
    contact_info: str = ""
    trusted_contact: str = ""


@router.get("/{username}/overview")
def get_patient_overview(username: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """One read-only request that composes the patient's current state.

    The UI should prefer this over fanning out to per-entity endpoints.
    Composed from existing repositories/services only; reuses the Phase 2
    patient-context builder for journals/moods/ring/followups and the
    timeline service for change metrics + events. No new data, no PATCH.
    """
    patient = PatientRepository(db).get_by_username(username)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if not _owns_or_psych(username, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    ctx = recent_patient_context(db, username, journal_limit=10, mood_limit=14, ring_limit=7, include_followups=True)

    identity = {
        "username": patient.username,
        "name": patient.name,
        "role": patient.role,
        "age": patient.age or 0,
        "occupation": patient.occupation or "",
        "clinic": patient.clinic_code or "",
        "assigned_psych": patient.assigned_psych or "",
        "onboarding_step": patient.onboarding_step or 0,
    }

    bookings = BookingRepository(db).get_for_patient(username)
    last_appointment = None
    if bookings:
        b = bookings[0]
        last_appointment = {
            "date": b.date,
            "time": b.time,
            "session_type": b.session_type or "",
            "status": b.status,
            "psychologist_username": b.psychologist_username or "",
        }

    clinical_brief = None
    if ctx.journals:
        j = ctx.journals[0]
        clinical_brief = {
            "journal_id": j.id,
            "summary": j.summary or "",
            "clinical_summary": j.clinical_summary or "",
            "emotions": j.emotions or "",
            "ai_source": j.ai_source or "",
            "timestamp": j.timestamp,
        }

    followup_list = [
        {
            "id": f.id,
            "title": f.title,
            "status": f.status,
            "grade": f.grade or "",
            "assigned_at": f.assigned_at or "",
            "completed_at": f.completed_at or "",
        }
        for f in ctx.followups
    ]
    followup_progress = {
        "total": len(followup_list),
        "pending": sum(1 for f in followup_list if f["status"] == "pending"),
        "completed": sum(1 for f in followup_list if f["status"] == "completed"),
        "list": followup_list,
    }

    metrics = compute_change_metrics(username, db)
    changes = {
        "mood_trend": metrics.mood_trend,
        "mood_change_pct": metrics.mood_change_pct,
        "current_mood_avg": metrics.current_mood_avg,
        "previous_mood_avg": metrics.previous_mood_avg,
        "journal_count_7": metrics.journal_count_7,
        "journal_count_14": metrics.journal_count_14,
        "engagement_trend": metrics.engagement_trend,
    }

    mood_trend = [{"date": m.date, "emoji": m.emoji, "label": m.label, "timestamp": m.timestamp} for m in ctx.moods]

    timeline = [
        {"type": e.type, "timestamp": e.timestamp, "data": e.data} for e in build_timeline_events(username, 30, db)
    ]

    sensor_trends = [
        {
            "bpm": r.bpm or 0,
            "stress": r.stress or 0,
            "sleep_hours": r.sleep_hours or 0,
            "spo2": r.spo2 or 0,
            "hrv": r.hrv or 0,
            "logged_at": r.logged_at,
        }
        for r in ctx.ring_logs
    ]

    risk = None
    latest_risk = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.patient_username == username)
        .order_by(RiskAssessment.created_at.desc())
        .first()
    )
    if latest_risk:
        risk = {
            "journal_id": latest_risk.journal_id,
            "risk_score": latest_risk.risk_score or 0,
            "triggered": bool(latest_risk.triggered),
            "confidence": latest_risk.confidence or 0.0,
            "explanation": latest_risk.explanation or "",
            "algorithm_version": latest_risk.algorithm_version or "",
            "created_at": latest_risk.created_at,
        }

    crisis = None
    state = db.query(CrisisState).filter(CrisisState.active == 1, CrisisState.patient_username == username).first()
    if state:
        crisis = {
            "active": True,
            "triggered_at": state.triggered_at or "",
            "acknowledged": bool(state.acknowledged),
            "helpline_escalated": bool(state.helpline_escalated),
            "trusted_contact_notified": bool(state.trusted_contact_notified),
            "trustee_acknowledged": bool(state.trustee_acknowledged),
        }

    alerts = []
    if crisis:
        alerts.append("Active crisis — acknowledge or escalate immediately")
    if risk and risk["triggered"]:
        alerts.append(f"AI flagged crisis-level risk ({risk['risk_score']}/10)")
    elif risk and risk["risk_score"] >= 7:
        alerts.append(f"Elevated risk score ({risk['risk_score']}/10) — review latest journal")
    if followup_progress["pending"] > 0:
        alerts.append(f"{followup_progress['pending']} pending homework task(s)")
    if metrics.journal_count_7 == 0:
        alerts.append("No journal entries in the last 7 days")

    return ok(
        data={
            "patient": identity,
            "last_appointment": last_appointment,
            "clinical_brief": clinical_brief,
            "followups": followup_progress,
            "changes_since_last_visit": changes,
            "mood_trend": mood_trend,
            "timeline": timeline,
            "sensor_trends": sensor_trends,
            "risk": risk,
            "crisis": crisis,
            "alerts": alerts,
        }
    )


@router.put("/me/contact")
def update_contact(update: ContactUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = PatientRepository(db)
    db_user = repo.get_by_username(user.username)
    if db_user:
        db_user.contact_info = update.contact_info
        if update.trusted_contact:
            db_user.trusted_contact = update.trusted_contact
        db.commit()
        get_event_bus().emit("patient:contact_updated", username=user.username)
    return ok(message="Updated")


class OnboardingUpdate(BaseModel):
    step: int
    data: dict = {}


@router.put("/me/onboarding")
def update_onboarding(update: OnboardingUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = PatientRepository(db)
    db_user = repo.get_by_username(user.username)
    if db_user:
        db_user.onboarding_step = update.step
        db.commit()
        get_event_bus().emit("patient:onboarding_updated", username=user.username, step=update.step)
    return ok(data={"step": update.step}, message="Updated")


@router.get("/me/wellness")
def get_wellness(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ring_data = (
        db.query(RingSensorLog)
        .filter(RingSensorLog.patient_username == user.username)
        .order_by(RingSensorLog.logged_at.desc())
        .first()
    )
    moods = (
        db.query(MoodLog)
        .filter(MoodLog.patient_username == user.username)
        .order_by(MoodLog.timestamp.desc())
        .limit(7)
        .all()
    )
    journals_today = (
        db.query(JournalEntry)
        .filter(
            JournalEntry.patient_username == user.username,
            JournalEntry.timestamp.like(f"{datetime.now(UTC).strftime('%Y-%m-%d')}%"),
        )
        .count()
    )

    today_mood = None
    if moods:
        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        today_moods = [m for m in moods if m.date == today_str]
        if today_moods:
            today_mood = {"emoji": today_moods[0].emoji, "label": today_moods[0].label}

    return ok(
        data={
            "ring": {
                "bpm": ring_data.bpm if ring_data else 0,
                "stress": ring_data.stress if ring_data else 0,
                "sleep": ring_data.sleep_hours if ring_data else 0,
                "spo2": ring_data.spo2 if ring_data else 0,
                "hrv": ring_data.hrv if ring_data else 0,
            }
            if ring_data
            else None,
            "mood": today_mood,
            "journals_today": journals_today,
            "mood_trend": [{"date": m.date, "emoji": m.emoji, "label": m.label} for m in moods[:7]],
        }
    )


@router.post("/me/consent")
async def upload_consent(
    file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    content = await validate_file_upload(file)
    ext = os.path.splitext(file.filename or "pdf")[1]
    fname = f"consent_{user.username}{ext}"
    dest = os.path.join(CONSENT_DIR, fname)
    with open(dest, "wb") as f:
        f.write(content)
    user.consent_form = dest
    db.commit()
    return ok(data={"file_path": dest}, message="Consent form uploaded")


@router.post("/{username}/assign-psych")
def assign_psychologist(
    username: str,
    psych_username: str,
    user: User = Depends(require_role("psychologist")),
    db: Session = Depends(get_db),
):
    repo = PatientRepository(db)
    patient = repo.get_by_username(username)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.assigned_psych = psych_username
    db.commit()
    get_event_bus().emit(
        "patient:psych_assigned", patient_username=username, psych=psych_username, assigned_by=user.username
    )
    return ok(message=f"Assigned {psych_username} to {username}")
