from typing import Any

from pydantic import BaseModel


class APIResponse(BaseModel):
    success: bool
    message: str
    data: Any | None = None
    request_id: str | None = None


def ok(data: Any = None, message: str = "Success", request_id: str = "") -> dict:
    return APIResponse(
        success=True,
        message=message,
        data=data,
        request_id=request_id or None,
    ).model_dump(exclude_none=True)


def fail(message: str = "Error", request_id: str = "", data: Any = None) -> dict:
    return APIResponse(
        success=False,
        message=message,
        data=data,
        request_id=request_id or None,
    ).model_dump(exclude_none=True)
