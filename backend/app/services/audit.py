"""Centralized audit service with hash-chained tamper detection."""
from datetime import datetime, timezone
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
    db: Session | None = None,
) -> AuditLog:
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        prev = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        prev_hash = prev.curr_hash if prev else ""

        entry = AuditLog(
            timestamp=datetime.now(timezone.utc).isoformat(),
            user=user,
            role=role,
            action=action,
            resource=resource,
            resource_id=resource_id,
            severity=severity,
            status=status,
            ip=ip,
            details=details,
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
