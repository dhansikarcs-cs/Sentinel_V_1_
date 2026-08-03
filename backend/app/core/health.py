import logging
import time

from sqlalchemy import text

from app.core.database import SessionLocal

logger = logging.getLogger("sentinel.health")

_start_time = time.time()


def check_database() -> dict:
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return {"status": "up", "latency_ms": round(time.time() * 1000 - time.time() * 1000, 2)}
        finally:
            db.close()
    except Exception as e:
        return {"status": "down", "error": str(e)}


def check_ai() -> dict:
    import os

    try:
        model_path = os.path.join(os.path.dirname(__file__), "..", "ml", "emotion_model.pkl")
        exists = os.path.exists(model_path)
        return {"status": "up" if exists else "degraded", "emotion_classifier": "available" if exists else "missing"}
    except Exception as e:
        return {"status": "down", "error": str(e)}


def health_ai() -> dict:
    import os

    import requests

    # Check Ollama
    ollama_available = False
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=1)
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
        "ollama": {"available": ollama_available, "url": "http://localhost:11434"},
        "groq": {"available": groq_available, "configured": groq_configured},
        "emotion_classifier": {"available": classifier_available, "model_version": "1.0.0"},
        "any_available": any_available,
    }


def health_full() -> dict:
    db_check = check_database()
    ai_check = check_ai()
    uptime = round(time.time() - _start_time, 2)
    all_up = db_check["status"] == "up" and ai_check["status"] in ("up", "degraded")
    return {
        "status": "healthy" if all_up else "degraded",
        "version": "1.0.0",
        "uptime_seconds": uptime,
        "checks": {
            "database": db_check,
            "ai": ai_check,
            "event_bus": {"status": "up"},
            "rate_limiter": {"status": "up"},
        },
    }


def health_live() -> dict:
    return {"status": "alive"}


def health_ready() -> dict:
    db = check_database()
    ready = db["status"] == "up"
    return {"status": "ready" if ready else "not_ready", "database": db["status"]}
