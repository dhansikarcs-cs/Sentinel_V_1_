import os
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.api_response import ok
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.input_validator import validate_file_upload
from app.events import get_event_bus
from app.ml.crisis_policy import CRISIS_POLICY
from app.models.ai_analysis import AIAnalysis
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


# Decision-prioritization thresholds (single owner for the overview derivation).
PRIORITY_OVERDUE_MEDIUM_DAYS = 5
PRIORITY_OVERDUE_HIGH_DAYS = 7
SLEEP_DROP_HOURS = 1.5
STRESS_HIGH = 70
BPM_HIGH = 100
SPO2_LOW = 94
_LEVEL_ORDER = {"high": 0, "medium": 1, "low": 2}


def derive_priorities(
    crisis: dict | None,
    risk: dict | None,
    followups: list[dict],
    changes: dict,
    ring_logs: list[RingSensorLog],
) -> list[dict]:
    """Rank the handful of things a clinician must attend to right now.

    Pure composition of already-derived overview data (Constitution #6: the
    backend derives, the frontend displays). Every item is explainable —
    it carries its own {reason, evidence, action} so the clinician can see
    *why* it was surfaced and *what* to do, without trusting a black box.
    Returns a sorted, de-duplicated list capped at 6.
    """
    items: list[dict] = []

    if crisis and crisis["active"]:
        items.append(
            {
                "level": "high",
                "title": "Active crisis",
                "reason": "Crisis protocol is active for this patient",
                "evidence": f"Triggered {crisis.get('triggered_at', '')[:10]} · "
                f"{'acknowledged' if crisis.get('acknowledged') else 'NOT acknowledged'}",
                "action": "Acknowledge or escalate immediately",
            }
        )

    if risk:
        score = risk.get("risk_score") or 0
        if risk.get("triggered") or score >= CRISIS_POLICY.auto_trigger_threshold:
            items.append(
                {
                    "level": "high",
                    "title": f"Crisis-level risk ({score}/10)",
                    "reason": f"Latest risk assessment scored {score}/10",
                    "evidence": f"Engine v{risk.get('algorithm_version') or '?'} · "
                    f"confidence {(risk.get('confidence') or 0) * 100:.0f}%",
                    "action": "Review latest journal now",
                }
            )
        elif CRISIS_POLICY.should_notify(score):
            items.append(
                {
                    "level": "high",
                    "title": f"Elevated risk score ({score}/10)",
                    "reason": f"Latest risk assessment scored {score}/10",
                    "evidence": f"Engine v{risk.get('algorithm_version') or '?'} · "
                    f"confidence {(risk.get('confidence') or 0) * 100:.0f}%",
                    "action": "Review latest journal during consultation",
                }
            )
        elif CRISIS_POLICY.should_warn(score):
            items.append(
                {
                    "level": "medium",
                    "title": f"Rising risk score ({score}/10)",
                    "reason": f"Latest risk assessment scored {score}/10",
                    "evidence": f"Engine v{risk.get('algorithm_version') or '?'}",
                    "action": "Monitor latest journal",
                }
            )

    overdue = []
    today = date.today()
    for f in followups:
        if f.get("status") != "pending" or not f.get("assigned_at"):
            continue
        try:
            days = (today - date.fromisoformat(f["assigned_at"][:10])).days
        except ValueError:
            days = 0
        if days >= PRIORITY_OVERDUE_MEDIUM_DAYS:
            overdue.append((f, days))
    if overdue:
        worst, worst_days = max(overdue, key=lambda x: x[1])
        items.append(
            {
                "level": "high" if worst_days >= PRIORITY_OVERDUE_HIGH_DAYS else "medium",
                "title": f"Follow-up overdue ({worst_days}d)",
                "reason": f"Pending homework task assigned {worst_days} days ago",
                "evidence": worst.get("title", ""),
                "action": "Review with patient or update the task",
            }
        )

    if changes.get("mood_trend") == "declining":
        pct = abs(changes.get("mood_change_pct") or 0)
        items.append(
            {
                "level": "medium",
                "title": "Mood declining",
                "reason": f"Mood score down {pct:.1f}% vs previous period",
                "evidence": f"Now {changes.get('current_mood_avg') or '—'}/5 vs previous "
                f"{changes.get('previous_mood_avg') or '—'}/5",
                "action": "Review during consultation",
            }
        )

    if len(ring_logs) >= 2:
        prev, latest = ring_logs[1], ring_logs[0]
        if prev.sleep_hours and latest.sleep_hours and prev.sleep_hours - latest.sleep_hours >= SLEEP_DROP_HOURS:
            items.append(
                {
                    "level": "medium",
                    "title": "Sleep dropped",
                    "reason": "Latest ring reading shows less sleep than the previous one",
                    "evidence": f"{prev.sleep_hours:.1f}h → {latest.sleep_hours:.1f}h",
                    "action": "Discuss sleep pattern in session",
                }
            )
        if latest.stress and latest.stress >= STRESS_HIGH:
            items.append(
                {
                    "level": "medium",
                    "title": f"Elevated stress ({latest.stress}/100)",
                    "reason": "Latest ring reading shows high stress",
                    "evidence": f"Stress {latest.stress}/100",
                    "action": "Check in on current stressors",
                }
            )
        if latest.bpm and latest.bpm >= BPM_HIGH:
            items.append(
                {
                    "level": "medium",
                    "title": f"Elevated heart rate ({latest.bpm} bpm)",
                    "reason": "Latest ring reading shows high heart rate",
                    "evidence": f"{latest.bpm} bpm",
                    "action": "Verify reading with patient",
                }
            )
        if latest.spo2 is not None and latest.spo2 and latest.spo2 < SPO2_LOW:
            items.append(
                {
                    "level": "medium",
                    "title": f"Low SpO2 ({latest.spo2}%)",
                    "reason": "Latest ring reading shows low oxygen saturation",
                    "evidence": f"SpO2 {latest.spo2}%",
                    "action": "Flag for clinical follow-up",
                }
            )

    if changes.get("journal_count_14") and changes.get("journal_count_7", 0) < changes["journal_count_14"] / 2:
        items.append(
            {
                "level": "medium",
                "title": "Engagement declining",
                "reason": "Journal activity is down vs the previous week",
                "evidence": f"{changes.get('journal_count_7', 0)} entries in 7d vs "
                f"{changes.get('journal_count_14', 0)} in 14d",
                "action": "Encourage re-engagement after the session",
            }
        )

    if not items:
        items.append(
            {
                "level": "low",
                "title": "No urgent items",
                "reason": "No signals crossed attention thresholds",
                "evidence": "Risk, mood, ring and follow-up signals are stable",
                "action": "Continue standard follow-up",
            }
        )

    seen = set()
    ranked = []
    for item in items:
        if item["title"] in seen:
            continue
        seen.add(item["title"])
        ranked.append(item)
    ranked.sort(key=lambda item: _LEVEL_ORDER.get(item["level"], 2))
    return ranked[:6]


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
        ai = db.query(AIAnalysis).filter(AIAnalysis.journal_id == j.id).order_by(AIAnalysis.created_at.desc()).first()
        clinical_brief = {
            "journal_id": j.id,
            "summary": j.summary or "",
            "clinical_summary": j.clinical_summary or "",
            "emotions": j.emotions or "",
            "ai_source": j.ai_source or "",
            "timestamp": j.timestamp,
            "ai_analysis": {
                "provider": ai.provider if ai else "",
                "confidence": ai.confidence if ai else 0.0,
                "model_version": ai.model_version if ai else "",
                "prompt_version": ai.prompt_version if ai else "",
                "priority": ai.priority if ai else "",
                "explanation": ai.explanation if ai else "",
            },
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
    elif risk and CRISIS_POLICY.should_elevate_alert(risk["risk_score"]):
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
            "priorities": derive_priorities(crisis, risk, followup_list, changes, ctx.ring_logs),
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
