"""Plain-English insights for psychologists.

The clinician's page should read like a colleague's note, not a spreadsheet.
This service turns the same derived data (mood, engagement, emotions, risk,
sensor, follow-ups) into a short human-language narrative. When an LLM is
available it writes the narrative from the facts; otherwise a deterministic
template does. The raw numbers stay available as evidence elsewhere.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.services import ai_service

logger = logging.getLogger("sentinel.plain_insights")

PLAIN_INSIGHTS_PROMPT_V1 = """You are a caring, experienced psychologist writing a short update for a colleague.

Use ONLY the facts below. Write in simple, warm English a first-time reader would understand.
Avoid jargon. Avoid raw percentages and probabilities unless they matter (then say them plainly, e.g. "8 out of 10").
Do not invent anything that is not in the facts.

Facts about {name} (age {age}):
- Mood trend: {mood_trend} (now about {current_mood}/5, before {previous_mood}/5)
- Journal engagement: {journal7} entries in the last 7 days, {journal14} in 14
- Most common feelings lately: {top_emotions}
- Recent emotion changes: {emotion_shifts}
- Latest risk score: {risk_score} out of 10 ({risk_words}){crisis_note}
- Latest ring reading: {sensor}
- Homework tasks: {followups}

Respond with valid JSON only:
{{"headline": "one short sentence summing up how she is doing overall",
  "insights": ["3-5 plain sentences, each about one area: mood, engagement, feelings, risk, sleep/health, homework"],
  "suggestion": "one short sentence on what to do next, plain and practical"}}"""


def _risk_words(score: int) -> str:
    if score >= 8:
        return "critical - needs immediate attention"
    if score >= 7:
        return "high - review her latest entries soon"
    if score >= 6:
        return "elevated - worth discussing in session"
    if score >= 4:
        return "moderate"
    return "low"


def _mood_sentence(trend: str, now, prev) -> str:
    if trend == "improving":
        return f"Her mood has been improving over the past two weeks (about {now}/5 lately)."
    if trend == "declining":
        return f"Her mood has dipped recently - from about {prev}/5 to about {now}/5."
    if now:
        return f"Her mood has stayed fairly steady at about {now}/5."
    return "There isn't enough mood data yet to see a trend."


def _engagement_sentence(journal7: int, journal14: int) -> str:
    if journal7 == 0 and journal14 == 0:
        return "She has not written in her journal recently - it may help to check in."
    if journal7 == 0:
        return f"She has not journaled in the past week, though she did earlier this month ({journal14} entries in 14 days)."
    if journal14 == 0:
        return f"She has written {journal7} journal entries in the last week."
    return f"She has been engaged - {journal7} journal entries in the last week ({journal14} in 14 days)."


def _emotions_sentence(top: list[str], shifts: list[str]) -> str:
    parts = []
    if top:
        joined = ", ".join(f"'{e}'" for e in top)
        parts.append(f"Her most common feelings lately have been {joined}.")
    if shifts:
        parts.append(shifts[0])
    return " ".join(parts) if parts else "There is not enough journal data yet to read her feelings."


def _risk_sentence(score: int | None, risk_words: str, crisis_active: bool) -> str:
    if crisis_active:
        return "A crisis alert is active - this takes priority over everything else."
    if score is None:
        return "No risk assessment has been done for her yet."
    if score == 0:
        return "Risk currently reads 0 out of 10 - nothing concerning."
    return f"Risk currently reads {score} out of 10 - {risk_words}."


def _sensor_sentence(sensor: dict | None) -> str:
    if not sensor:
        return "No ring readings yet."
    bits = []
    if sensor.get("bpm"):
        bits.append(f"heart rate {sensor['bpm']} bpm")
    if sensor.get("stress"):
        bits.append(f"stress {sensor['stress']}")
    if sensor.get("sleep_hours"):
        bits.append(f"{sensor['sleep_hours']}h sleep")
    if sensor.get("spo2"):
        bits.append(f"oxygen {sensor['spo2']}%")
    if not bits:
        return "Ring connected, but no useful readings yet."
    return f"Latest ring reading looks normal ({', '.join(bits)})."


def _followups_sentence(pending: int, completed: int) -> str:
    if pending and completed:
        return f"She has {pending} homework task(s) waiting and {completed} completed."
    if pending:
        return f"She has {pending} homework task(s) waiting to do."
    if completed:
        return f"She has finished {completed} homework task(s)."
    return "No homework tasks assigned yet."


def _suggestion(crisis_active: bool, score: int | None, trend: str, journal7: int) -> str:
    if crisis_active:
        return "Acknowledge the crisis alert and reach out to her as soon as possible."
    if score is not None and score >= 7:
        return "Review her latest journal entry and, if appropriate, schedule an early session."
    if trend == "declining" or (journal7 == 0):
        return "Check in with her this week - a short session could help get things back on track."
    if trend == "improving":
        return "No urgent action needed. Keep encouraging her to keep up the good habits."
    return "Nothing urgent right now. A brief check-in during your next session would help."


def _fallback(pack: dict[str, Any]) -> dict[str, Any]:
    score = pack.get("risk_score")
    crisis_active = bool(pack.get("crisis_active"))
    trend = pack.get("mood_trend", "stable")
    now = pack.get("current_mood")
    prev = pack.get("previous_mood")
    journal7 = pack.get("journal_count_7") or 0
    top = pack.get("top_emotions") or []
    shifts = pack.get("emotion_shifts") or []
    pending = pack.get("followups_pending") or 0
    completed = pack.get("followups_completed") or 0

    name = pack.get("name") or "This patient"
    if crisis_active:
        headline = f"{name} needs urgent attention right now - a crisis alert is active."
    elif score is not None and score >= 8:
        headline = f"{name}'s latest writing shows critical risk - please act on this today."
    elif score is not None and score >= 7:
        headline = f"{name} is showing some concern - worth looking at her latest entries."
    elif trend == "improving":
        headline = f"{name} is moving in a good direction - mood and engagement look positive."
    elif trend == "declining":
        headline = f"{name} seems to be having a tougher stretch lately - mood has dipped."
    else:
        headline = f"{name} is in a steady place at the moment - nothing urgent to act on."

    insights = [
        _mood_sentence(trend, now, prev),
        _engagement_sentence(journal7, pack.get("journal_count_14") or 0),
        _emotions_sentence(top, shifts),
        _risk_sentence(score, _risk_words(score) if score is not None else "", crisis_active),
        _sensor_sentence(pack.get("sensor")),
        _followups_sentence(pending, completed),
    ]

    return {
        "headline": headline,
        "insights": insights,
        "suggestion": _suggestion(crisis_active, score, trend, journal7),
    }


def _extract_json(text: str) -> dict[str, Any] | None:
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        data = json.loads(text[start : end + 1])
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        return None
    return None


def generate_plain_insights(pack: dict[str, Any]) -> dict[str, Any]:
    """Return a plain-English narrative built from the given fact pack.

    Prefers an LLM (Ollama, then Groq) to phrase the narrative; falls back to
    deterministic templates. `source` tells the UI whether a model wrote it.
    """
    now_iso = datetime.now(UTC).isoformat()
    fallback = _fallback(pack)
    if not pack.get("allow_ai", True):
        return {"source": "rule", "provider": "rule", "prompt_version": "rule", "generated_at": now_iso, **fallback}

    prompt = PLAIN_INSIGHTS_PROMPT_V1.format(
        name=pack.get("name") or "this patient",
        age=pack.get("age") or "?",
        mood_trend=pack.get("mood_trend") or "unknown",
        current_mood=pack.get("current_mood") or "?",
        previous_mood=pack.get("previous_mood") or "?",
        journal7=pack.get("journal_count_7") or 0,
        journal14=pack.get("journal_count_14") or 0,
        top_emotions=", ".join(pack.get("top_emotions") or []) or "none yet",
        emotion_shifts="; ".join(pack.get("emotion_shifts") or []) or "none",
        risk_score=pack.get("risk_score") if pack.get("risk_score") is not None else "none yet",
        risk_words=_risk_words(pack.get("risk_score")) if pack.get("risk_score") is not None else "no assessment yet",
        crisis_note=" - A CRISIS ALERT IS ACTIVE, address this first" if pack.get("crisis_active") else "",
        sensor=_sensor_sentence(pack.get("sensor")) if pack.get("sensor") else "no ring readings yet",
        followups=_followups_sentence(pack.get("followups_pending") or 0, pack.get("followups_completed") or 0),
    )

    provider = ""
    output = ai_service._query_ollama(prompt, timeout=25, prompt_version="plain_insights/v1")
    if output:
        provider = "ollama"
    if not output:
        output = ai_service._query_groq(prompt, timeout=25, prompt_version="plain_insights/v1")
        if output:
            provider = "groq"

    if not provider:
        return {"source": "rule", "provider": "rule", "prompt_version": "rule", "generated_at": now_iso, **fallback}

    parsed = _extract_json(output)
    if not parsed or not parsed.get("headline"):
        return {
            "source": "rule",
            "provider": provider,
            "prompt_version": "plain_insights/v1",
            "generated_at": now_iso,
            **fallback,
        }

    insights = parsed.get("insights")
    if not isinstance(insights, list) or not all(isinstance(i, str) for i in insights):
        insights = fallback["insights"]

    return {
        "source": "ai",
        "provider": provider,
        "prompt_version": "plain_insights/v1",
        "generated_at": now_iso,
        "headline": parsed["headline"],
        "insights": insights,
        "suggestion": parsed.get("suggestion") or fallback["suggestion"],
    }
