import hashlib
import hmac as hmac_mod
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.api_response import ok
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.crisis import CrisisLog, CrisisState
from app.models.user import User
from app.schemas.crisis import CrisisLogResponse, CrisisRiskResponse, CrisisStateResponse, RiskAssessmentRequest
from app.services.ai_service import assess_crisis_risk
from app.services.audit import log_audit
from app.services.notification import send_email

logger = logging.getLogger("sentinel.crisis")

router = APIRouter(prefix="/crisis", tags=["crisis"])

TRUSTEE_PORTAL_BASE = settings.sentinel_ack_link


def _trustee_hmac_key() -> bytes:
    return (settings.trustee_link_secret or settings.jwt_secret).encode("utf-8")


def _make_trustee_link(patient: str) -> str:
    """One-time, expiring, signed trustee link. The signature binds patient + expiry
    so a leaked link cannot be replayed indefinitely or re-pointed at another patient."""
    exp = int((datetime.now(UTC) + timedelta(seconds=settings.trustee_link_expire_seconds)).timestamp())
    message = f"{patient}|{exp}"
    sig = hmac_mod.new(_trustee_hmac_key(), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{TRUSTEE_PORTAL_BASE}?patient={patient}&exp={exp}&sig={sig}"


def _verify_trustee_link(patient: str, exp: int, sig: str) -> bool:
    if not patient or not exp or not sig:
        return False
    if datetime.now(UTC).timestamp() > exp:
        return False
    message = f"{patient}|{exp}"
    expected = hmac_mod.new(_trustee_hmac_key(), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac_mod.compare_digest(expected, sig)


def _require_valid_trustee_link(
    patient: str = Query(""),
    exp: int = Query(0),
    sig: str = Query(""),
) -> str:
    if not _verify_trustee_link(patient, exp, sig):
        raise HTTPException(status_code=403, detail="Invalid or expired trustee link")
    return patient


def _get_or_create_state(db: Session, patient: str) -> CrisisState:
    """Fetch (or create) the crisis state row for a specific patient.

    Unlike the old single-row model, each patient owns their own CrisisState row,
    so multiple patients can hold an active crisis concurrently without overwriting
    one another.
    """
    state = db.query(CrisisState).filter(CrisisState.patient_username == patient).first()
    if not state:
        state = CrisisState(active=0, patient_username=patient)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def _active_state_for(db: Session, patient: str = "") -> CrisisState | None:
    """Resolve the crisis state a caller should see.

    Priority:
      1. An explicitly requested patient with an active crisis.
      2. The caller's own active crisis (patients see their own).
      3. The single currently-active row (backward compatible when one
         crisis is active and the caller is a psychologist without a row).
    """
    if patient:
        state = db.query(CrisisState).filter(CrisisState.patient_username == patient).first()
        if state and state.active:
            return state
        return state or _get_or_create_state(db, patient)
    active = db.query(CrisisState).filter(CrisisState.active == 1).first()
    return active if active else _get_or_create_state(db, "")


@router.get("/state", response_model=CrisisStateResponse)
def get_crisis_state(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _active_state_for(db) if user.role == "psychologist" else _get_or_create_state(db, user.username)
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
    state = _get_or_create_state(db, user.username)
    now = datetime.now(UTC).isoformat()
    state.active = 1
    state.patient_username = user.username
    state.triggered_at = now
    state.triggered_by = user.role
    state.acknowledged = 0
    state.acknowledged_by = ""
    state.acknowledged_at = ""
    state.trusted_contact_notified = 0
    state.trustee_acknowledged = 0
    state.trustee_clicked = 0
    state.helpline_escalated = 0
    state.tc_ack_emailed = 0
    state.helpline_ack_emailed = 0
    log = CrisisLog(event="triggered", patient=user.username, timestamp=now, source=user.role)
    db.add(log)
    db.commit()
    log_audit("crisis_triggered", user=user.username, role=user.role, severity="HIGH", status="success", db=db)
    return ok(message="Crisis triggered")


@router.post("/acknowledge")
def acknowledge_crisis(
    patient: str = Query(""),
    user: User = Depends(require_role("psychologist")),
    db: Session = Depends(get_db),
):
    state = _active_state_for(db, patient)
    if not state.active:
        return ok(message="No active crisis")
    now = datetime.now(UTC).isoformat()
    state.acknowledged = 1
    state.acknowledged_by = user.username
    state.acknowledged_at = now
    log = CrisisLog(event="acknowledged", patient=state.patient_username, timestamp=now, source=user.username)
    db.add(log)
    db.commit()
    log_audit(
        "crisis_acknowledged",
        user=user.username,
        role=user.role,
        severity="HIGH",
        status="success",
        resource=state.patient_username,
        db=db,
    )
    return ok(message="Crisis acknowledged")


@router.post("/resolve")
def resolve_crisis(
    patient: str = Query(""),
    user: User = Depends(require_role("psychologist")),
    db: Session = Depends(get_db),
):
    state = _active_state_for(db, patient)
    if not state.active:
        return ok(message="No active crisis")
    now = datetime.now(UTC).isoformat()
    patient = state.patient_username
    log = CrisisLog(
        event="resolved", patient=patient, timestamp=now, source=user.username, details=f"by {user.username}"
    )
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
    log_audit(
        "crisis_resolved",
        user=user.username,
        role=user.role,
        severity="HIGH",
        status="success",
        resource=patient,
        db=db,
    )
    return ok(message="Crisis resolved")


@router.post("/trustee-acknowledge")
def trustee_acknowledge(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _active_state_for(db, user.username if user.role != "psychologist" else "")
    if not state.active:
        return ok(message="No active crisis")
    now = datetime.now(UTC).isoformat()
    state.trustee_acknowledged = 1
    log = CrisisLog(
        event="trustee_acknowledged",
        patient=state.patient_username,
        timestamp=now,
        source=user.username,
        details="Trusted contact acknowledged",
    )
    db.add(log)
    db.commit()
    return ok(message="Trustee acknowledged")


@router.post("/trustee-clicked")
def trustee_clicked(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _active_state_for(db, user.username if user.role != "psychologist" else "")
    if not state.active:
        return ok(message="No active crisis")
    now = datetime.now(UTC).isoformat()
    if not state.trustee_clicked:
        state.trustee_clicked = 1
        log = CrisisLog(
            event="trustee_clicked",
            patient=state.patient_username,
            timestamp=now,
            source=user.username,
            details="Trusted contact clicked notification",
        )
        db.add(log)
        db.commit()
    return ok(message="Trustee clicked")


@router.post("/notify-trusted-contact")
def notify_trusted_contact(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _active_state_for(db, user.username if user.role != "psychologist" else "")
    if not state.active:
        return ok(message="No active crisis")
    now = datetime.now(UTC).isoformat()
    patient = db.query(User).filter(User.username == state.patient_username).first()
    tc_email = patient.trusted_contact if patient else ""
    email_sent = False
    if tc_email:
        trustee_link = _make_trustee_link(state.patient_username)
        email_sent = send_email(
            to=tc_email,
            subject="[Sentinel] Crisis Alert — Your loved one needs you",
            body=f"Sentinel Crisis Alert\n\nPatient: {state.patient_username}\nTime: {now}\n\nYour loved one has triggered a crisis alert through Sentinel. Please reach out to them as soon as possible.\n\nAcknowledge this alert: {trustee_link}\n\n- Sentinel Safety System",
        )
    state.trusted_contact_notified = 1
    log = CrisisLog(
        event="trusted_contact_notified",
        patient=state.patient_username,
        timestamp=now,
        source=user.username,
        details=f"Trusted contact {'emailed' if email_sent else 'logged (no SMTP)'}",
    )
    db.add(log)
    db.commit()
    return ok(data={"email_sent": email_sent}, message="Trusted contact notified")


@router.get("/public-state")
def public_crisis_state(
    patient: str = Depends(_require_valid_trustee_link),
    db: Session = Depends(get_db),
):
    state = _get_or_create_state(db, patient)
    return {
        "active": bool(state.active),
        "patient": state.patient_username or "",
        "triggered_at": state.triggered_at or "",
        "acknowledged": bool(state.acknowledged),
        "trustee_acknowledged": bool(state.trustee_acknowledged),
        "trustee_clicked": bool(state.trustee_clicked),
    }


@router.post("/public-trustee-acknowledge")
def public_trustee_acknowledge(
    patient: str = Depends(_require_valid_trustee_link),
    db: Session = Depends(get_db),
):
    state = _get_or_create_state(db, patient)
    if state.patient_username != patient or not state.active:
        return ok(message="No active crisis")
    now = datetime.now(UTC).isoformat()
    state.trustee_acknowledged = 1
    log = CrisisLog(
        event="trustee_acknowledged",
        patient=state.patient_username,
        timestamp=now,
        source="trustee_portal",
        details="Trusted contact acknowledged via portal",
    )
    db.add(log)
    db.commit()
    return ok(message="Trustee acknowledged")


@router.post("/public-trustee-clicked")
def public_trustee_clicked(
    patient: str = Depends(_require_valid_trustee_link),
    db: Session = Depends(get_db),
):
    state = _get_or_create_state(db, patient)
    if state.patient_username != patient or not state.active:
        return ok(message="No active crisis")
    now = datetime.now(UTC).isoformat()
    if not state.trustee_clicked:
        state.trustee_clicked = 1
        log = CrisisLog(
            event="trustee_clicked",
            patient=state.patient_username,
            timestamp=now,
            source="trustee_portal",
            details="Trusted contact clicked notification link",
        )
        db.add(log)
        db.commit()
    return ok(message="Trustee clicked")


@router.post("/helpline-escalate")
def helpline_escalate(
    patient: str = Query(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    state = _active_state_for(db, patient or (user.username if user.role != "psychologist" else ""))
    if not state.active:
        return ok(message="No active crisis")
    now = datetime.now(UTC).isoformat()
    helpline = settings.helpline_email or settings.email_from
    email_sent = send_email(
        to=helpline,
        subject="[Sentinel] CRISIS ESCALATION — Immediate attention required",
        body=f"Sentinel Crisis Escalation\n\nPatient: {state.patient_username}\nTriggered at: {state.triggered_at}\n\nThis patient has not been acknowledged within the safety window. Immediate helpline intervention is required.\n\nAcknowledge: {_make_trustee_link(state.patient_username)}\n\n- Sentinel Safety System",
    )
    state.helpline_escalated = 1
    log = CrisisLog(
        event="helpline_escalated",
        patient=state.patient_username,
        timestamp=now,
        source=user.username,
        details=f"Helpline {'emailed' if email_sent else 'logged (no SMTP)'}",
    )
    db.add(log)
    db.commit()
    log_audit(
        "crisis_helpline_escalated",
        user=user.username,
        role=user.role,
        severity="HIGH",
        status="success",
        resource=state.patient_username,
        db=db,
    )
    return ok(data={"email_sent": email_sent}, message="Helpline escalated")


def _handle_escalation(state: CrisisState, db: Session):
    if not state.active or state.acknowledged:
        return
    try:
        triggered = datetime.fromisoformat(state.triggered_at)
        elapsed = int((datetime.now(UTC) - triggered).total_seconds())
    except Exception:
        return

    if elapsed >= 30 and not state.trusted_contact_notified:
        state.trusted_contact_notified = 1
        patient = db.query(User).filter(User.username == state.patient_username).first()
        tc_email = patient.trusted_contact if patient else ""
        email_sent = False
        if tc_email:
            trustee_link = _make_trustee_link(state.patient_username)
            email_sent = send_email(
                tc_email,
                "[Sentinel] Crisis Alert — Your loved one needs you",
                f"Sentinel Crisis Alert\n\nPatient: {state.patient_username}\nTime: {datetime.now(UTC).isoformat()}\n\nYour loved one has triggered a crisis alert. Please reach out to them as soon as possible.\n\nAcknowledge this alert: {trustee_link}\n\n- Sentinel Safety System",
            )
        log = CrisisLog(
            event="trustee_notified_auto",
            patient=state.patient_username,
            timestamp=datetime.now(UTC).isoformat(),
            source="system",
            details=f"Trusted contact {'emailed' if email_sent else 'logged (no SMTP)'}",
        )
        db.add(log)

    if elapsed >= 60 and not state.helpline_escalated:
        state.helpline_escalated = 1
        helpline = settings.helpline_email or settings.email_from
        email_sent = send_email(
            helpline,
            "[Sentinel] CRISIS ESCALATION — Immediate attention required",
            f"Sentinel Crisis Escalation\n\nPatient: {state.patient_username}\nTriggered at: {state.triggered_at}\n\nNo acknowledgement within 60s. Immediate helpline intervention required.\n\nAcknowledge: {_make_trustee_link(state.patient_username)}\n\n- Sentinel Safety System",
        )
        log = CrisisLog(
            event="helpline_escalated_auto",
            patient=state.patient_username,
            timestamp=datetime.now(UTC).isoformat(),
            source="system",
            details=f"Helpline {'emailed' if email_sent else 'logged (no SMTP)'}",
        )
        db.add(log)

    db.commit()


@router.get("/elapsed")
def crisis_elapsed(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _active_state_for(db) if user.role == "psychologist" else _get_or_create_state(db, user.username)
    _handle_escalation(state, db)
    if not state.active or not state.triggered_at:
        return {"elapsed": 0, "stage": "inactive", "is_active": False}
    try:
        triggered = datetime.fromisoformat(state.triggered_at)
        elapsed = int((datetime.now(UTC) - triggered).total_seconds())
    except Exception:
        elapsed = 0

    if state.acknowledged:
        stage = "acknowledged"
    elif state.helpline_escalated or elapsed >= 60:
        stage = "helpline_escalated"
    elif elapsed >= 30 and (state.trustee_clicked or state.trustee_acknowledged):
        stage = "trustee_coming"
    elif state.trustee_clicked:
        stage = "trustee_clicked"
    elif state.trusted_contact_notified or elapsed >= 30:
        stage = "trustee_notified"
    else:
        stage = "triggered"

    return {"elapsed": elapsed, "stage": stage, "is_active": True, "patient": state.patient_username}


@router.post("/assess-risk", response_model=CrisisRiskResponse)
def assess_risk(req: RiskAssessmentRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = assess_crisis_risk(req.text)
    return CrisisRiskResponse(**result)


@router.get("/log", response_model=list[CrisisLogResponse])
def get_crisis_log(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = db.query(CrisisLog).order_by(CrisisLog.timestamp.desc()).limit(50).all()
    return logs
