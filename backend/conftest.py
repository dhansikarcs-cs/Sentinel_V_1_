import os
import sys
import uuid
from pathlib import Path

WORKDIR = Path(__file__).resolve().parent

os.environ["DATABASE_URL"] = f"sqlite:///{WORKDIR / 'data' / ('pytest_' + uuid.uuid4().hex[:8] + '.db')}"
os.environ.setdefault("JWT_SECRET", "pytest-secret-not-for-production")

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.core.idempotency import idempotency_store
from app.core.login_rate_limiter import login_rate_limiter
from app.core.rate_limiter import RateLimiterMiddleware
from app.main import app
from app.services import ai_service

os.makedirs(WORKDIR / "data", exist_ok=True)


async def _noop_dispatch(self, request, call_next):
    return await call_next(request)


RateLimiterMiddleware.dispatch = _noop_dispatch


class _FakeLoop:
    def create_task(self, coro, *args, **kwargs):
        if hasattr(coro, "close"):
            try:
                coro.close()
            except Exception:
                pass
        return None


@pytest.fixture(autouse=True)
def _isolate_ai(monkeypatch):
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: _FakeLoop())
    monkeypatch.setattr(ai_service, "_query_ollama", lambda *a, **k: None)
    yield


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    idempotency_store._store.clear()
    login_rate_limiter._attempts.clear()
    login_rate_limiter._lockouts.clear()
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    from app.core.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def make_user(client):
    def _make(username=None, role="patient", **overrides):
        username = username or f"user_{uuid.uuid4().hex[:8]}"
        payload = {
            "username": username,
            "password": "Str0ng!Pass1",
            "name": "Test User",
            "role": role,
            "age": 30,
            "occupation": "Engineer",
            "clinic_code": "SENTINEL-TEST",
            **overrides,
        }
        resp = client.post("/api/auth/register", json=payload)
        assert resp.status_code == 200, resp.text
        login = client.post(
            "/api/auth/login",
            json={"username": username, "password": payload["password"]},
        )
        assert login.status_code == 200, login.text
        data = login.json()
        return {
            "username": username,
            "password": payload["password"],
            "role": role,
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
        }

    return _make


@pytest.fixture()
def patient_user(make_user):
    return make_user(role="patient")


@pytest.fixture()
def psych_user(make_user):
    return make_user(role="psychologist")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
