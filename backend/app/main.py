import logging
import os
import traceback
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    activity,
    agents,
    ai_analyses,
    auth,
    bookings,
    crisis,
    discrepancy,
    emotion_results,
    emotions,
    event_store_api,
    export_data,
    feature_flags_api,
    followups,
    journal,
    ml_registry,
    mood,
    notifications,
    patients,
    psych_journal,
    psychologists,
    ring,
    risk_assessments,
    search_api,
    sensor_readings,
    sync_api,
    timeline,
    triage,
    ws,
)
from app.core.api_gateway import APIGatewayMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.core.health import health_ai, health_full, health_live, health_ready
from app.core.logging_config import configure_logging
from app.core.rate_limiter import RateLimiterMiddleware
from app.core.request_id import RequestIDMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.structured_errors import ErrorCode, make_error
from app.events import get_event_bus
from app.events.subscribers import register_all_subscribers

logger = logging.getLogger("sentinel")

configure_logging()


def _init_db():
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if "change-me-in-production" in settings.jwt_secret:
        logger.warning("JWT secret is still set to default — override via JWT_SECRET env var before deploying")
    _init_db()
    register_all_subscribers(get_event_bus())
    logger.info("Event subscribers registered")
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(APIGatewayMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimiterMiddleware, max_requests=100, window_seconds=60)

origins = [o.strip() for o in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ----- Global exception handlers (prevents stack trace leakage) -----


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    rid = getattr(request.state, "request_id", "")
    logger.warning("Validation error on %s %s request_id=%s: %s", request.method, request.url.path, rid, exc.errors())
    return JSONResponse(
        status_code=422,
        content=make_error(ErrorCode.VALIDATION_ERROR, "Invalid request parameters", rid),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    rid = getattr(request.state, "request_id", "")
    code_map = {
        404: ErrorCode.NOT_FOUND,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        429: ErrorCode.RATE_LIMITED,
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=make_error(code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR), str(exc.detail), rid),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error(
        "Unhandled exception on %s %s request_id=%s: %s", request.method, request.url.path, rid, traceback.format_exc()
    )
    return JSONResponse(
        status_code=500,
        content=make_error(ErrorCode.INTERNAL_ERROR, "Internal server error — the team has been notified.", rid),
    )


# ── API v1 versioned router ──────────────────────────────────────
v1_router = APIRouter(prefix="/api")

v1_router.include_router(auth.router)
v1_router.include_router(patients.router)
v1_router.include_router(psychologists.router)
v1_router.include_router(journal.router)
v1_router.include_router(mood.router)
v1_router.include_router(crisis.router)
v1_router.include_router(bookings.router)
v1_router.include_router(followups.router)
v1_router.include_router(ring.router)
v1_router.include_router(timeline.router)
v1_router.include_router(ws.router)
v1_router.include_router(discrepancy.router)
v1_router.include_router(agents.router)
v1_router.include_router(triage.router)
v1_router.include_router(activity.router)
v1_router.include_router(export_data.router)
v1_router.include_router(psych_journal.router)
v1_router.include_router(emotions.router)
v1_router.include_router(emotion_results.router)
v1_router.include_router(ai_analyses.router)
v1_router.include_router(sensor_readings.router)
v1_router.include_router(risk_assessments.router)
v1_router.include_router(notifications.router)
v1_router.include_router(ml_registry.router)
v1_router.include_router(event_store_api.router)
v1_router.include_router(feature_flags_api.router)
v1_router.include_router(search_api.router)
v1_router.include_router(sync_api.router)

app.include_router(v1_router)


@app.get("/health")
def health():
    return health_full()


@app.get("/health/live")
def health_live_endpoint():
    return health_live()


@app.get("/health/ready")
def health_ready_endpoint():
    return health_ready()


@app.get("/api/ai/health")
def ai_health():
    return health_ai()


# ── Serve frontend static files (production) ──────────────────────
_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _DIST.exists():
    _ASSETS = _DIST / "assets"
    if _ASSETS.exists():
        app.mount("/assets", StaticFiles(directory=str(_ASSETS)), name="static-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="Not Found")
        file = _DIST / full_path
        if file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(_DIST / "index.html"))
