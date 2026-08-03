import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("sentinel.gateway")


class APIGatewayMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        if path.startswith("/api/"):
            version = self._extract_version(path)
            request.state.api_version = version
            request.state.gateway_routed = True

        response: Response = await call_next(request)

        if hasattr(request.state, "api_version"):
            response.headers["X-API-Version"] = request.state.api_version

        return response

    def _extract_version(self, path: str) -> str:
        parts = path.strip("/").split("/")
        if len(parts) >= 2 and parts[1].startswith("v"):
            return parts[1]
        return "v1"
