import logging
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger("sentinel.rate_limiter")


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int | None = None, window_seconds: int | None = None):
        super().__init__(app)
        self.max_requests = max_requests if max_requests is not None else settings.rate_limit_max
        self.window_seconds = window_seconds if window_seconds is not None else settings.rate_limit_window
        self.requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health",):
            return await call_next(request)

        # Health / device pushes authenticate via X-Device-Token (not IP), so the
        # shared per-IP limiter would wrongly throttle many devices behind one
        # gateway. Only IP-limit unauthenticated paths.
        p = request.url.path
        if p.endswith("/ring/data") and (
            request.headers.get("X-Device-Serial") and request.headers.get("X-Device-Token")
        ):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window_seconds
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > window_start]

        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {client_ip} on {request.method} {request.url.path}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests — try again shortly."},
                headers={"Retry-After": str(self.window_seconds)},
            )

        self.requests[client_ip].append(now)
        return await call_next(request)
