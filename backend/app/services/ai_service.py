import json
import re
import urllib.request
from typing import Optional

from app.core.config import settings


def _query_ollama(prompt: str, timeout: int = 15) -> Optional[str]:
    try:
        data = json.dumps({"model": settings.ollama_model, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(
            f"{settings.ollama_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        result = json.loads(resp.read().decode())
        return result.get("response", "")
    except Exception:
        return None


CRISIS_KW = ["suicide", "kill myself", "end my life", "want to die", "not worth living", "self-harm", "hurt myself", "emergency", "can't take it", "overdose"]
HIGH_KW = ["panic", "hopeless", "desperate", "terrified", "screaming", "can't breathe", "alone", "scared", "anxiety", "afraid", "worthless", "numb"]
MEDIUM_KW = ["sad", "worried", "tired", "stress", "overwhelmed", "frustrated", "angry", "upset", "crying", "lost"]
SOCIAL_KW = ["friends", "family", "people", "nobody", "alone", "isolated", "no one", "lonely", "withdrew"]
SLEEP_KW = ["sleep", "insomnia", "tired", "exhausted", "can't sleep", "wake up", "nightmare"]
ACTIVITY_KW = ["nothing", "didn't do", "stay in bed", "no energy", "can't", "avoid", "skipped"]


def _compute_contributing_factors(text: str) -> dict:
    lower = text.lower()
    return {
        "crisis_keywords": [kw for kw in CRISIS_KW if kw in lower],
        "high_risk_keywords": [kw for kw in HIGH_KW if kw in lower],
        "moderate_keywords": [kw for kw in MEDIUM_KW if kw in lower],
        "social_withdrawal": sum(1 for kw in SOCIAL_KW if kw in lower),
        "sleep_disturbance": sum(1 for kw in SLEEP_KW if kw in lower),
        "activity_decline": sum(1 for kw in ACTIVITY_KW if kw in lower),
    }


def assess_crisis_risk(text: str) -> dict:
    if not text.strip():
        return {"risk_score": 1, "reasoning": "No content to assess.", "triggered": False, "contributing_factors": {}}

    factors = _compute_contributing_factors(text)

    prompt = (
        "You are Sentinel. Assess crisis risk in this journal entry. "
        "Return ONLY a valid JSON object with three fields: "
        '"risk_score" (integer 1-10), "reasoning" (string), '
        '"contributing_factors" (object with keys like sentiment, emotions_detected, key_triggers). '
        f"\n\nJournal Entry:\n{text}\n\n"
        "Example: {\"risk_score\": 7, \"reasoning\": \"Fear and sadness detected.\", \"contributing_factors\": {\"sentiment\": \"negative\", \"emotions_detected\": [\"fear\"], \"key_triggers\": [\"hopelessness\"]}}"
    )

    raw = _query_ollama(prompt)
    if raw:
        match = re.search(r'\{[^{}]*"risk_score"[^{}]*"reasoning"[^{}]*\}', raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result.get("risk_score"), (int, float)):
                    result["risk_score"] = int(result["risk_score"])
                    result["triggered"] = result["risk_score"] >= 8
                    if "contributing_factors" not in result:
                        result["contributing_factors"] = factors
                    return result
            except Exception:
                pass

    return _fallback_risk_assessment(text, factors)


def _fallback_risk_assessment(text: str, factors: dict = None) -> dict:
    if factors is None:
        factors = _compute_contributing_factors(text)

    score = 1
    if factors.get("crisis_keywords"):
        score = 10
    elif factors.get("high_risk_keywords"):
        score = 7
    elif factors.get("moderate_keywords"):
        score = 4
    if factors.get("social_withdrawal", 0) >= 2 or factors.get("sleep_disturbance", 0) >= 2 or factors.get("activity_decline", 0) >= 2:
        score = max(score, 5)

    factor_lines = []
    if factors["crisis_keywords"]:
        factor_lines.append(f"CRISIS keywords: {', '.join(factors['crisis_keywords'])}")
    if factors["high_risk_keywords"]:
        factor_lines.append(f"High-risk: {', '.join(factors['high_risk_keywords'][:3])}")
    if factors["moderate_keywords"]:
        factor_lines.append(f"Moderate: {', '.join(factors['moderate_keywords'][:3])}")
    if factors["social_withdrawal"] >= 2:
        factor_lines.append(f"Social withdrawal ({factors['social_withdrawal']}x)")
    if factors["sleep_disturbance"] >= 2:
        factor_lines.append(f"Sleep disturbance ({factors['sleep_disturbance']}x)")
    if factors["activity_decline"] >= 2:
        factor_lines.append(f"Activity decline ({factors['activity_decline']}x)")

    return {
        "risk_score": score,
        "reasoning": f"Score {score}/10. {'; '.join(factor_lines) if factor_lines else 'No significant indicators.'}",
        "triggered": score >= 8,
        "contributing_factors": factors,
    }


def summarize_journal(text: str) -> dict:
    if not text.strip():
        return {"summary": text, "ai_source": "rule", "emotions": "", "source": "rule"}

    prompt = (
        "You are Sentinel. Summarize this journal entry in 1-2 sentences clinically. "
        "Return valid JSON: {\"summary\": \"...\", \"emotions\": \"comma,separated,emotions\"}. "
        f"\n\n{text}"
    )

    raw = _query_ollama(prompt)
    if raw:
        match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                return {"summary": result.get("summary", text[:200]), "ai_source": "ollama", "emotions": result.get("emotions", ""), "source": "ai"}
            except Exception:
                pass

    return {"summary": text[:200], "ai_source": "rule", "emotions": "", "source": "rule"}
