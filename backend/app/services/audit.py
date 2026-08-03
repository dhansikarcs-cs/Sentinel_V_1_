"""Centralized audit service with hash-chained tamper detection."""

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.audit import AuditLog


def log_audit(
    action: str,
    user: str = "",
    role: str = "",
    resource: str = "",
    resource_id: str = "",
    severity: str = "INFO",
    status: str = "success",
    ip: str = "",
    details: str = "",
    device: str = "",
    browser: str = "",
    session_id: str = "",
    before_value: str = "",
    after_value: str = "",
    request_id: str = "",
    db: Session | None = None,
) -> AuditLog:
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        prev = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        prev_hash = prev.curr_hash if prev else ""

        rich_details = details
        if any([device, browser, session_id, before_value, after_value, request_id]):
            payload = {}
            if device:
                payload["device"] = device
            if browser:
                payload["browser"] = browser
            if session_id:
                payload["session_id"] = session_id
            if before_value:
                payload["before"] = before_value
            if after_value:
                payload["after"] = after_value
            if request_id:
                payload["request_id"] = request_id
            if details:
                payload["extra"] = details
            rich_details = json.dumps(payload) if payload else details

        entry = AuditLog(
            timestamp=datetime.now(UTC).isoformat(),
            user=user,
            role=role,
            action=action,
            resource=resource,
            resource_id=resource_id,
            severity=severity,
            status=status,
            ip=ip,
            details=rich_details,
            prev_hash=prev_hash,
            curr_hash="",
        )
        entry.curr_hash = entry.compute_hash()
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    finally:
        if own_session:
            db.close()
