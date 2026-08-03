from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User


def require_owner_or_role(*roles: str):
    def _check(
        resource_username: str,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if user.username == resource_username:
            return user
        if user.role in roles:
            return user
        log_idor_attempt(user.username, resource_username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource",
        )
    return _check


def verify_patient_owns_or_psychologist(
    patient_username: str,
    user: User = Depends(get_current_user),
) -> User:
    if user.username == patient_username:
        return user
    if user.role == "psychologist":
        return user
    log_idor_attempt(user.username, patient_username)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to access this resource",
    )


def log_idor_attempt(attacker_username: str, target_username: str):
    try:
        from app.services.audit import log_audit
        log_audit(
            "idor_blocked",
            user=attacker_username,
            severity="WARNING",
            status="blocked",
            resource="patient_resource",
            resource_id=target_username,
            details=f"IDOR attempt by {attacker_username} targeting {target_username}",
        )
    except Exception:
        pass
