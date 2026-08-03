import uuid
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("sentinel.request_id")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        logger.info(
            "request_start method=%s path=%s request_id=%s client=%s",
            request.method,
            request.url.path,
            request_id,
            request.client.host if request.client else "unknown",
        )
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
