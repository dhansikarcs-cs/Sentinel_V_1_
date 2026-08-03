import json
import re
import time
import urllib.request
from collections import deque
from threading import Lock

from app.core.config import settings
from app.ml.emotion_classifier import EmotionClassifier
from app.ml.risk_engine import assess_risk_with_explainability

_ollama_lock = Lock()
_ollama_queue: deque = deque()
_ollama_last_call = 0.0

_emotion_clf = EmotionClassifier()


def _query_ollama(prompt: str, timeout: int = 20) -> str | None:
    global _ollama_last_call
    with _ollama_lock:
        now = time.time()
        if now - _ollama_last_call < 0.5:
            time.sleep(0.5 - (now - _ollama_last_call))
        _ollama_last_call = time.time()
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


def _query_groq(prompt: str, timeout: int = 20) -> str:
    key = settings.groq_api_key or ""
    if not key or key == "gsk_your_key_here":
        return ""
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
        return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except Exception:
        return ""


def _query_ai(prompt: str, timeout: int = 20) -> str:
    result = _query_ollama(prompt, timeout=timeout)
    if result:
        return result
    result = _query_groq(prompt, timeout=timeout)
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
        }

    top_emotions, emotion_probs = classify_emotions_with_probs(text)
    emotions_str = ", ".join(e for e, p in top_emotions if e != "neutral") or "neutral"
    emotion_probs_json = json.dumps(emotion_probs)

    emotion_hint = f"\nEmotions detected: {emotions_str}." if emotions_str else ""

    if mode == "clinical":
        prompt = (
            "You are Sentinel, a clinical documentation AI. Read this journal entry "
            "and write a brief clinical summary (2-4 sentences)."
            f"{emotion_hint}"
            " Use clinical tone, third person, past tense. Do not quote verbatim."
            ' Return valid JSON: {"summary": "..."}.'
            f"\n\nJournal Entry:\n{text}"
        )
    else:
        prompt = (
            "You are Sentinel, a friendly AI companion, not a therapist. "
            "Read this journal entry and reply like a warm, supportive friend "
            "sending a text message (2-4 short sentences)."
            f"{emotion_hint}"
            " Be casual and conversational, the way a close friend talks. "
            "You can use playful or affectionate language. "
            "Do NOT sound clinical, professional, or like a psychologist. "
            "No advice whatsoever — "
            "no suggestions, no 'try this', no 'consider that', no 'remember to', "
            "no coping techniques, no deep breaths. Zero prescription. Just be there for them."
            ' Return valid JSON: {"summary": "..."}.'
            f"\n\nJournal Entry:\n{text}"
        )

    raw = _query_ollama(prompt, timeout=15)
    source = "ollama"
    if not raw or _is_raw_echo(raw, text):
        raw = _query_groq(prompt)
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
        }
    if mode == "clinical":
        summary = (
            f"Observations: Patient reports emotional experiences "
            f"consistent with {emotions if emotions else 'mixed affect'}.\n\n"
            f"Assessment: Emotional awareness present. Continue monitoring.\n\n"
            f"Plan: Follow-up within standard interval."
        )
    else:
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
    }


def synthesize_clinical_notes(raw_notes: str) -> str:
    if not raw_notes.strip():
        return "No notes to synthesize."

    prompt = (
        "You are Sentinel. Convert these session notes into a structured clinical note "
        "with Observations, Assessment, and Plan sections. Use precise emotion language "
        "in the Assessment. Keep it professional but not cold.\n\n"
        f"Session Notes:\n{raw_notes}\n\nStructured Clinical Note:"
    )

    result = _query_ai(prompt)
    if result:
        return result

    return (
        f"**Observations**: {raw_notes[:200]}{'...' if len(raw_notes) > 200 else ''}\n\n"
        f"**Assessment**: Patient appears engaged in therapeutic process. "
        f"Continue monitoring emotional trajectory.\n\n"
        f"**Plan**: Follow-up session recommended within standard interval."
    )
