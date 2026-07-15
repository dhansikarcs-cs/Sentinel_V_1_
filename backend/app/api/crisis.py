from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.crisis import CrisisState, CrisisLog
from app.schemas.crisis import CrisisStateResponse, CrisisRiskResponse, CrisisLogResponse, RiskAssessmentRequest
from app.services.ai_service import assess_crisis_risk
from app.services.audit import log_audit

router = APIRouter(prefix="/crisis", tags=["crisis"])


def _get_or_create_state(db: Session) -> CrisisState:
    state = db.query(CrisisState).first()
    if not state:
        state = CrisisState(active=0)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


@router.get("/state", response_model=CrisisStateResponse)
def get_crisis_state(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _get_or_create_state(db)
    return CrisisStateResponse(
        active=bool(state.active),
        patient=state.patient_username or "",
        triggered_at=state.triggered_at or "",
        triggered_by=state.triggered_by or "",
        acknowledged=bool(state.acknowledged),
        acknowledged_by=state.acknowledged_by or "",
        acknowledged_at=state.acknowledged_at or "",
        helpline_escalated=bool(state.helpline_escalated),
        trusted_contact_notified=bool(state.trusted_contact_notified),
        trustee_acknowledged=bool(state.trustee_acknowledged),
        trustee_clicked=bool(state.trustee_clicked),
    )


@router.post("/trigger")
def trigger_crisis(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _get_or_create_state(db)
    now = datetime.now(timezone.utc).isoformat()
    state.active = 1
    state.patient_username = user.username
    state.triggered_at = now
    state.triggered_by = user.role
    state.acknowledged = 0
    state.trusted_contact_notified = 0
    state.trustee_acknowledged = 0
    state.trustee_clicked = 0
    state.helpline_escalated = 0
    log = CrisisLog(event="triggered", patient=user.username, timestamp=now, source=user.role)
    db.add(log)
    db.commit()
    log_audit("crisis_triggered", user=user.username, role=user.role, action="trigger", severity="HIGH", status="success", db=db)
    return {"message": "Crisis triggered"}


@router.post("/acknowledge")
def acknowledge_crisis(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    state = _get_or_create_state(db)
    if not state.active:
        return {"message": "No active crisis"}
    now = datetime.now(timezone.utc).isoformat()
    state.acknowledged = 1
    state.acknowledged_by = user.username
    state.acknowledged_at = now
    log = CrisisLog(event="acknowledged", patient=state.patient_username, timestamp=now, source=user.username)
    db.add(log)
    db.commit()
    log_audit("crisis_acknowledged", user=user.username, role=user.role, action="acknowledge", severity="HIGH", status="success", resource=state.patient_username, db=db)
    return {"message": "Crisis acknowledged"}


@router.post("/resolve")
def resolve_crisis(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    state = _get_or_create_state(db)
    if not state.active:
        return {"message": "No active crisis"}
    now = datetime.now(timezone.utc).isoformat()
    patient = state.patient_username
    log = CrisisLog(event="resolved", patient=patient, timestamp=now, source=user.username, details=f"by {user.username}")
    state.active = 0
    state.patient_username = ""
    state.triggered_at = ""
    state.triggered_by = ""
    state.acknowledged = 0
    state.acknowledged_by = ""
    state.acknowledged_at = ""
    state.helpline_escalated = 0
    state.trusted_contact_notified = 0
    state.trustee_acknowledged = 0
    state.trustee_clicked = 0
    state.tc_ack_emailed = 0
    state.helpline_ack_emailed = 0
    db.add(log)
    db.commit()
    log_audit("crisis_resolved", user=user.username, role=user.role, action="resolve", severity="HIGH", status="success", resource=patient, db=db)
    return {"message": "Crisis resolved"}


@router.post("/assess-risk", response_model=CrisisRiskResponse)
def assess_risk(req: RiskAssessmentRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = assess_crisis_risk(req.text)
    return CrisisRiskResponse(**result)


@router.get("/log", response_model=list[CrisisLogResponse])
def get_crisis_log(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = db.query(CrisisLog).order_by(CrisisLog.timestamp.desc()).limit(50).all()
    return logs
