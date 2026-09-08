"""Shared authorization helpers.

Ownership rule across the API: a caller may access a patient's data only when
they ARE that patient, or they hold the psychologist role.
"""

from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.models.user import User


def owns_or_psych(username: str, user: User) -> bool:
    return user.username == username or user.role == "psychologist"


def ensure_owns_or_psych(username: str, user: User) -> None:
    if user.role != "psychologist" and user.username != username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def get_owner_or_psych(username: str, user: User = Depends(get_current_user)) -> User:
    ensure_owns_or_psych(username, user)
    return user
