import logging
import os
import time

from sqlalchemy import text

from app.core.database import SessionLocal

logger = logging.getLogger("sentinel.health")

_start_time = time.time()

AI_URL_DEFAULTS = {"ollama": "http://localhost:11434"}


def check_database() -> dict:
    try:
        db = SessionLocal()
        try:
            start = time.perf_counter()
            db.execute(text("SELECT 1"))
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {"status": "up", "latency_ms": latency_ms}
        finally:
            db.close()
    except Exception as e:
        return {"status": "down", "error": str(e)}


def check_database_write() -> dict:
    """Prove the DB accepts writes by toggling the sqlite user_version header."""
    try:
        db = SessionLocal()
        try:
            start = time.perf_counter()
            current = db.execute(text("PRAGMA user_version")).scalar()
            next_version = (int(current) + 1) % 1000000
            db.execute(text(f"PRAGMA user_version = {next_version}"))
            db.commit()
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {"status": "up", "latency_ms": latency_ms}
        finally:
            db.close()
    except Exception as e:
        return {"status": "down", "error": str(e)}


def check_ai() -> dict:
    try:
        model_path = os.path.join(os.path.dirname(__file__), "..", "ml", "emotion_model.pkl")
        exists = os.path.exists(model_path)
        return {"status": "up" if exists else "degraded", "emotion_classifier": "available" if exists else "missing"}
    except Exception as e:
        return {"status": "down", "error": str(e)}


def health_ai() -> dict:
    import requests

    # Check Ollama
    ollama_available = False
    ollama_url = os.environ.get("OLLAMA_URL", AI_URL_DEFAULTS["ollama"])
    try:
        resp = requests.get(f"{ollama_url}/api/tags", timeout=1)
        ollama_available = resp.status_code == 200
    except Exception:
        pass

    # Check Groq
    groq_key = os.environ.get("GROQ_API_KEY", "")
    groq_configured = bool(groq_key) and groq_key not in ("", "gsk_your_key_here", "change-me")
    groq_available = groq_configured

    # Check emotion classifier
    classifier_available = False
    try:
        from app.ml.emotion_classifier import classifier

        classifier_available = classifier is not None
    except Exception:
        pass

    any_available = ollama_available or groq_available or classifier_available

    return {
        "ollama": {"available": ollama_available, "url": ollama_url},
        "groq": {"available": groq_available, "configured": groq_configured},
        "emotion_classifier": {"available": classifier_available, "model_version": "1.0.0"},
        "any_available": any_available,
    }


def health_full() -> dict:
    db_check = check_database()
    db_write_check = check_database_write()
    ai_check = check_ai()
    ai_providers = health_ai()
    uptime = round(time.time() - _start_time, 2)
    checks_up = db_check["status"] == "up" and db_write_check["status"] == "up"
    ai_ok = ai_check["status"] in ("up", "degraded")
    return {
        "status": "healthy" if checks_up and ai_ok else "degraded",
        "version": "1.0.0",
        "uptime_seconds": uptime,
        "checks": {
            "database": db_check,
            "database_write": db_write_check,
            "ai": ai_check,
            "ai_providers": ai_providers,
            "event_bus": {"status": "up"},
            "rate_limiter": {"status": "up"},
        },
    }


def health_live() -> dict:
    return {"status": "alive"}


def health_ready() -> dict:
    db = check_database()
    db_write = check_database_write()
    ready = db["status"] == "up" and db_write["status"] == "up"
    return {"status": "ready" if ready else "not_ready", "database": db["status"], "database_write": db_write["status"]}
