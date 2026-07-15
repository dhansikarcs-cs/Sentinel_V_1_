import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, patients, psychologists, journal, mood, crisis, bookings, followups, ring, timeline, ws, discrepancy


def _init_db():
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_db()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
