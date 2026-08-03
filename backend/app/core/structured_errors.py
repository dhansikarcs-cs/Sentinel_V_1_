from typing import Any

from pydantic import BaseModel


class APIError(BaseModel):
    code: str
    message: str
    trace_id: str | None = None
    details: dict[str, Any] | None = None


class ErrorCode:
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    CRISIS_ACTIVE = "CRISIS_ACTIVE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    LOGIN_RATE_LIMITED = "LOGIN_RATE_LIMITED"
    PASSWORD_TOO_WEAK = "PASSWORD_TOO_WEAK"
    IDOR_BLOCKED = "IDOR_BLOCKED"
    SESSION_EXPIRED = "SESSION_EXPIRED"


def make_error(code: str, message: str, trace_id: str = "", details: dict = None) -> dict:
    return APIError(
        code=code,
        message=message,
        trace_id=trace_id or None,
        details=details,
    ).model_dump(exclude_none=True)
