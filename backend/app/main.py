import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, patients, psychologists, journal, mood, crisis, bookings, followups, ring, timeline, ws, discrepancy

logger = logging.getLogger("sentinel")


def _init_db():
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if "change-me-in-production" in settings.jwt_secret:
        logger.warning("JWT secret is still set to default — override via JWT_SECRET env var before deploying")
    _init_db()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(psychologists.router)
app.include_router(journal.router)
app.include_router(mood.router)
app.include_router(crisis.router)
app.include_router(bookings.router)
app.include_router(followups.router)
app.include_router(ring.router)
app.include_router(timeline.router)
app.include_router(ws.router)
app.include_router(discrepancy.router)


@app.get("/health")
def health():
    return {"status": "ok"}
