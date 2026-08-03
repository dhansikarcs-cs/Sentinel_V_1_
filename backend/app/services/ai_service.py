import json
import logging
import re
import time
import urllib.request
from threading import Lock

from app.core.config import settings
from app.ml.emotion_classifier import EmotionClassifier
from app.ml.risk_engine import assess_risk_with_explainability

logger = logging.getLogger("sentinel.ai")

_ollama_lock = Lock()
_ollama_last_call = 0.0

_emotion_clf = EmotionClassifier()

CLINICAL_JOURNAL_SUMMARY_PROMPT_V1 = (
    "You are Sentinel, a clinical documentation AI. Read this journal entry "
    "and write a brief clinical summary (2-4 sentences)."
    "{emotion_hint}"
    " Use clinical tone, third person, past tense. Do not quote verbatim."
    ' Return valid JSON: {"summary": "..."}.'
    "\n\nJournal Entry:\n{text}"
)
FRIENDLY_JOURNAL_SUMMARY_PROMPT_V1 = (
    "You are Sentinel, a friendly AI companion, not a therapist. "
    "Read this journal entry and reply like a warm, supportive friend "
    "sending a text message (2-4 short sentences)."
    "{emotion_hint}"
    " Be casual and conversational, the way a close friend talks. "
    "You can use playful or affectionate language. "
    "Do NOT sound clinical, professional, or like a psychologist. "
    "No advice whatsoever — "
    "no suggestions, no 'try this', no 'consider that', no 'remember to', "
    "no coping techniques, no deep breaths. Zero prescription. Just be there for them."
    ' Return valid JSON: {"summary": "..."}.'
    "\n\nJournal Entry:\n{text}"
)
NOTE_SYNTHESIS_PROMPT_V1 = (
    "You are Sentinel. Convert these session notes into a structured clinical note "
    "with Observations, Assessment, and Plan sections. Use precise emotion language "
    "in the Assessment. Keep it professional but not cold.\n\n"
    "Session Notes:\n{raw_notes}\n\nStructured Clinical Note:"
)


def _query_ollama(prompt: str, timeout: int = 20, prompt_version: str = "") -> str | None:
    global _ollama_last_call
    with _ollama_lock:
        now = time.time()
        if now - _ollama_last_call < 0.5:
            time.sleep(0.5 - (now - _ollama_last_call))
        _ollama_last_call = time.time()
    start = time.perf_counter()
    try:
        data = json.dumps({"model": settings.ollama_model, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(
            f"{settings.ollama_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        result = json.loads(resp.read().decode())
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "ai_request provider=ollama ok=true latency_ms=%s prompt_version=%s prompt_len=%s",
            latency_ms,
            prompt_version,
            len(prompt),
            extra={"extra_fields": {"provider": "ollama", "ok": True, "latency_ms": latency_ms}},
        )
        return result.get("response", "")
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "ai_request provider=ollama ok=false latency_ms=%s prompt_version=%s error=%s",
            latency_ms,
            prompt_version,
            e,
            extra={"extra_fields": {"provider": "ollama", "ok": False, "latency_ms": latency_ms, "error": str(e)}},
        )
        return None


def _query_groq(prompt: str, timeout: int = 20, prompt_version: str = "") -> str:
    key = settings.groq_api_key or ""
    if not key or key == "gsk_your_key_here":
        return ""
    start = time.perf_counter()
    try:
        data = json.dumps(
            {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 512,
            }
        ).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        result = json.loads(resp.read().decode())
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "ai_request provider=groq ok=true latency_ms=%s prompt_version=%s prompt_len=%s",
            latency_ms,
            prompt_version,
            len(prompt),
            extra={"extra_fields": {"provider": "groq", "ok": True, "latency_ms": latency_ms}},
        )
        return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "ai_request provider=groq ok=false latency_ms=%s prompt_version=%s error=%s",
            latency_ms,
            prompt_version,
            e,
            extra={"extra_fields": {"provider": "groq", "ok": False, "latency_ms": latency_ms, "error": str(e)}},
        )
        return ""


def _query_ai(prompt: str, timeout: int = 20, prompt_version: str = "") -> str:
    result = _query_ollama(prompt, timeout=timeout, prompt_version=prompt_version)
    if result:
        return result
    result = _query_groq(prompt, timeout=timeout, prompt_version=prompt_version)
    if result:
        return result
    return ""


def _is_raw_echo(output: str, original: str) -> bool:
    cleaned = output.strip().lower()
    orig_clean = original.strip().lower()
    if not cleaned or not orig_clean:
        return False
    if cleaned == orig_clean:
        return True
    if cleaned in orig_clean:
        return True
    if orig_clean in cleaned:
        return True
    out_words = set(re.findall(r"\w+", cleaned))
    orig_words = set(re.findall(r"\w+", orig_clean))
    if not orig_words:
        return False
    overlap = len(out_words & orig_words) / len(orig_words)
    return overlap > 0.85


def classify_emotions(text: str) -> str:
    top = _emotion_clf.predict_top(text, threshold=0.15)
    labels = [e for e, p in top if e != "neutral"]
    if not labels:
        return ""
    return ", ".join(labels[:5])


def classify_emotions_with_probs(text: str) -> tuple[list[tuple[str, float]], dict[str, float]]:
    probs = _emotion_clf.predict_proba(text)
    top = _emotion_clf.predict_top(text, threshold=0.15)
    return top, probs


def assess_crisis_risk(text: str) -> dict:
    return assess_risk_with_explainability(text)


def summarize_journal(text: str, mode: str = "patient") -> dict:
    if not text.strip():
        return {
            "summary": text[:200],
            "ai_source": "rule",
            "emotions": "",
            "emotion_probabilities": "{}",
            "source": "rule",
            "prompt_version": "rule",
        }

    top_emotions, emotion_probs = classify_emotions_with_probs(text)
    emotions_str = ", ".join(e for e, p in top_emotions if e != "neutral") or "neutral"
    emotion_probs_json = json.dumps(emotion_probs)

    emotion_hint = f"\nEmotions detected: {emotions_str}." if emotions_str else ""

    if mode == "clinical":
        prompt = CLINICAL_JOURNAL_SUMMARY_PROMPT_V1.format(emotion_hint=emotion_hint, text=text)
        prompt_version = "clinical_journal_summary/v1"
    else:
        prompt = FRIENDLY_JOURNAL_SUMMARY_PROMPT_V1.format(emotion_hint=emotion_hint, text=text)
        prompt_version = "friendly_journal_summary/v1"

    raw = _query_ollama(prompt, timeout=15, prompt_version=prompt_version)
    source = "ollama"
    if not raw or _is_raw_echo(raw, text):
        raw = _query_groq(prompt, prompt_version=prompt_version)
        source = "groq"
    if raw and not _is_raw_echo(raw, text):
        match = re.search(r"\{[^{}]+\}", raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                return {
                    "summary": result.get("summary", text[:200]),
                    "ai_source": source,
                    "emotions": emotions_str,
                    "emotion_probabilities": emotion_probs_json,
                    "source": "ai",
                    "prompt_version": prompt_version,
                }
            except Exception:
                pass

    return _fallback_summary(text, emotions_str, emotion_probs_json, mode)


def _fallback_summary(text: str, emotions: str = "", emotion_probs_json: str = "{}", mode: str = "patient") -> dict:
    if not text.strip():
        return {
            "summary": "No content to summarize.",
            "ai_source": "rule",
            "emotions": "",
            "emotion_probabilities": "{}",
            "source": "rule",
            "prompt_version": "rule",
        }
    if mode == "clinical":
        prompt_version = "clinical_journal_summary/v1"
        summary = (
            f"Observations: Patient reports emotional experiences "
            f"consistent with {emotions if emotions else 'mixed affect'}.\n\n"
            f"Assessment: Emotional awareness present. Continue monitoring.\n\n"
            f"Plan: Follow-up within standard interval."
        )
    else:
        prompt_version = "friendly_journal_summary/v1"
        if emotions:
            summary = f"You're feeling {emotions}. That's completely valid — thanks for sharing how you feel."
        else:
            summary = "Thanks for writing this entry. Your feelings matter and tracking them is a positive step."

    return {
        "summary": summary,
        "ai_source": "rule",
        "emotions": emotions,
        "emotion_probabilities": emotion_probs_json,
        "source": "rule",
        "prompt_version": prompt_version,
    }


def synthesize_clinical_notes(raw_notes: str) -> str:
    if not raw_notes.strip():
        return "No notes to synthesize."

    prompt = NOTE_SYNTHESIS_PROMPT_V1.format(raw_notes=raw_notes)
    prompt_version = "note_synthesis/v1"

    result = _query_ai(prompt, prompt_version=prompt_version)
    if result:
        return result

    return (
        f"**Observations**: {raw_notes[:200]}{'...' if len(raw_notes) > 200 else ''}\n\n"
        f"**Assessment**: Patient appears engaged in therapeutic process. "
        f"Continue monitoring emotional trajectory.\n\n"
        f"**Plan**: Follow-up session recommended within standard interval."
    )
