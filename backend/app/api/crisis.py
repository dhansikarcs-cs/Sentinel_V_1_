import smtplib
import os
import logging
from datetime import datetime, timezone
from email.message import EmailMessage
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.config import settings
from app.core.api_response import ok
from app.models.user import User
from app.models.crisis import CrisisState, CrisisLog
from app.schemas.crisis import CrisisStateResponse, CrisisRiskResponse, CrisisLogResponse, RiskAssessmentRequest
from app.services.ai_service import assess_crisis_risk
from app.services.audit import log_audit

logger = logging.getLogger("sentinel.crisis")

router = APIRouter(prefix="/crisis", tags=["crisis"])

TRUSTEE_PORTAL_BASE = os.environ.get("SENTINEL_ACK_LINK", "http://localhost:5173/trustee")


def _send_email(to: str, subject: str, body: str) -> bool:
    logger.info("=== CRISIS EMAIL ===")
    logger.info("To: %s", to)
    logger.info("Subject: %s", subject)
    logger.info("Body:\n%s", body)
    logger.info("====================")

    if not settings.smtp_host:
        logger.warning("SMTP not configured — email logged only")
        return False
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = to
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        logger.info("Email sent successfully to %s", to)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP auth failed — app password may be expired. Generate new one at https://myaccount.google.com/apppasswords")
        return False
    except Exception as e:
        logger.error("Email send failed: %s: %s", type(e).__name__, e)
        return False


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
    log_audit("crisis_triggered", user=user.username, role=user.role, severity="HIGH", status="success", db=db)
    return ok(message="Crisis triggered")


@router.post("/acknowledge")
def acknowledge_crisis(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    state = _get_or_create_state(db)
    if not state.active:
        return ok(message="No active crisis")
    now = datetime.now(timezone.utc).isoformat()
    state.acknowledged = 1
    state.acknowledged_by = user.username
    state.acknowledged_at = now
    log = CrisisLog(event="acknowledged", patient=state.patient_username, timestamp=now, source=user.username)
    db.add(log)
    db.commit()
    log_audit("crisis_acknowledged", user=user.username, role=user.role, severity="HIGH", status="success", resource=state.patient_username, db=db)
    return ok(message="Crisis acknowledged")


@router.post("/resolve")
def resolve_crisis(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    state = _get_or_create_state(db)
    if not state.active:
        return ok(message="No active crisis")
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
    log_audit("crisis_resolved", user=user.username, role=user.role, severity="HIGH", status="success", resource=patient, db=db)
    return ok(message="Crisis resolved")


@router.post("/trustee-acknowledge")
def trustee_acknowledge(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _get_or_create_state(db)
    if not state.active:
        return ok(message="No active crisis")
    now = datetime.now(timezone.utc).isoformat()
    state.trustee_acknowledged = 1
    log = CrisisLog(event="trustee_acknowledged", patient=state.patient_username, timestamp=now, source=user.username, details="Trusted contact acknowledged")
    db.add(log)
    db.commit()
    return ok(message="Trustee acknowledged")


@router.post("/trustee-clicked")
def trustee_clicked(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _get_or_create_state(db)
    if not state.active:
        return ok(message="No active crisis")
    now = datetime.now(timezone.utc).isoformat()
    state.trustee_clicked = 1
    log = CrisisLog(event="trustee_clicked", patient=state.patient_username, timestamp=now, source=user.username, details="Trusted contact clicked notification")
    db.add(log)
    db.commit()
    return ok(message="Trustee clicked")


@router.post("/notify-trusted-contact")
def notify_trusted_contact(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _get_or_create_state(db)
    if not state.active:
        return ok(message="No active crisis")
    now = datetime.now(timezone.utc).isoformat()
    patient = db.query(User).filter(User.username == state.patient_username).first()
    tc_email = patient.trusted_contact if patient else ""
    email_sent = False
    if tc_email:
        trustee_link = f"{TRUSTEE_PORTAL_BASE}?patient={state.patient_username}"
        email_sent = _send_email(
            to=tc_email,
            subject="[Sentinel] Crisis Alert — Your loved one needs you",
            body=f"Sentinel Crisis Alert\n\nPatient: {state.patient_username}\nTime: {now}\n\nYour loved one has triggered a crisis alert through Sentinel. Please reach out to them as soon as possible.\n\nAcknowledge this alert: {trustee_link}\n\n- Sentinel Safety System",
        )
    state.trusted_contact_notified = 1
    log = CrisisLog(event="trusted_contact_notified", patient=state.patient_username, timestamp=now, source=user.username, details=f"Trusted contact {'emailed' if email_sent else 'logged (no SMTP)'}")
    db.add(log)
    db.commit()
    return ok(data={"email_sent": email_sent}, message="Trusted contact notified")


@router.get("/public-state")
def public_crisis_state(db: Session = Depends(get_db)):
    state = _get_or_create_state(db)
    return {
        "active": bool(state.active),
        "patient": state.patient_username or "",
        "triggered_at": state.triggered_at or "",
        "acknowledged": bool(state.acknowledged),
        "trustee_acknowledged": bool(state.trustee_acknowledged),
        "trustee_clicked": bool(state.trustee_clicked),
    }


@router.post("/public-trustee-acknowledge")
def public_trustee_acknowledge(db: Session = Depends(get_db)):
    state = _get_or_create_state(db)
    if not state.active:
        return ok(message="No active crisis")
    now = datetime.now(timezone.utc).isoformat()
    state.trustee_acknowledged = 1
    log = CrisisLog(event="trustee_acknowledged", patient=state.patient_username, timestamp=now, source="trustee_portal", details="Trusted contact acknowledged via portal")
    db.add(log)
    db.commit()
    return ok(message="Trustee acknowledged")


@router.post("/public-trustee-clicked")
def public_trustee_clicked(db: Session = Depends(get_db)):
    state = _get_or_create_state(db)
    if not state.active:
        return ok(message="No active crisis")
    now = datetime.now(timezone.utc).isoformat()
    if not state.trustee_clicked:
        state.trustee_clicked = 1
        log = CrisisLog(event="trustee_clicked", patient=state.patient_username, timestamp=now, source="trustee_portal", details="Trusted contact clicked notification link")
        db.add(log)
        db.commit()
    return ok(message="Trustee clicked")


@router.post("/helpline-escalate")
def helpline_escalate(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _get_or_create_state(db)
    if not state.active:
        return ok(message="No active crisis")
    now = datetime.now(timezone.utc).isoformat()
    helpline = settings.helpline_email or settings.email_from
    email_sent = _send_email(
        to=helpline,
        subject="[Sentinel] CRISIS ESCALATION — Immediate attention required",
        body=f"Sentinel Crisis Escalation\n\nPatient: {state.patient_username}\nTriggered at: {state.triggered_at}\n\nThis patient has not been acknowledged within the safety window. Immediate helpline intervention is required.\n\nAcknowledge: {TRUSTEE_PORTAL_BASE}?patient={state.patient_username}\n\n- Sentinel Safety System",
    )
    state.helpline_escalated = 1
    log = CrisisLog(event="helpline_escalated", patient=state.patient_username, timestamp=now, source=user.username, details=f"Helpline {'emailed' if email_sent else 'logged (no SMTP)'}")
    db.add(log)
    db.commit()
    log_audit("crisis_helpline_escalated", user=user.username, role=user.role, severity="HIGH", status="success", resource=state.patient_username, db=db)
    return ok(data={"email_sent": email_sent}, message="Helpline escalated")


def _handle_escalation(state: CrisisState, db: Session):
    if not state.active or state.acknowledged:
        return
    try:
        triggered = datetime.fromisoformat(state.triggered_at)
        elapsed = int((datetime.now(timezone.utc) - triggered).total_seconds())
    except:
        return

    if elapsed >= 30 and not state.trusted_contact_notified:
        state.trusted_contact_notified = 1
        patient = db.query(User).filter(User.username == state.patient_username).first()
        tc_email = patient.trusted_contact if patient else ""
        if tc_email:
            trustee_link = f"{TRUSTEE_PORTAL_BASE}?patient={state.patient_username}"
            _send_email(tc_email,
                "[Sentinel] Crisis Alert — Your loved one needs you",
                f"Sentinel Crisis Alert\n\nPatient: {state.patient_username}\nTime: {datetime.now(timezone.utc).isoformat()}\n\nYour loved one has triggered a crisis alert. Please reach out to them as soon as possible.\n\nAcknowledge this alert: {trustee_link}\n\n- Sentinel Safety System")
        log = CrisisLog(event="trustee_notified_auto", patient=state.patient_username, timestamp=datetime.now(timezone.utc).isoformat(), source="system")
        db.add(log)

    if elapsed >= 60 and not state.helpline_escalated:
        state.helpline_escalated = 1
        helpline = settings.helpline_email or settings.email_from
        _send_email(helpline,
            "[Sentinel] CRISIS ESCALATION — Immediate attention required",
            f"Sentinel Crisis Escalation\n\nPatient: {state.patient_username}\nTriggered at: {state.triggered_at}\n\nNo acknowledgement within 60s. Immediate helpline intervention required.\n\nAcknowledge: {TRUSTEE_PORTAL_BASE}?patient={state.patient_username}\n\n- Sentinel Safety System")
        log = CrisisLog(event="helpline_escalated_auto", patient=state.patient_username, timestamp=datetime.now(timezone.utc).isoformat(), source="system")
        db.add(log)

    db.commit()


@router.get("/elapsed")
def crisis_elapsed(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _get_or_create_state(db)
    _handle_escalation(state, db)
    if not state.active or not state.triggered_at:
        return {"elapsed": 0, "stage": "inactive", "is_active": False}
    try:
        triggered = datetime.fromisoformat(state.triggered_at)
        elapsed = int((datetime.now(timezone.utc) - triggered).total_seconds())
    except:
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
