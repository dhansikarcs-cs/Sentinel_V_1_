import os
import streamlit as st

CACHE_SIZE = 20
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "sentinel"


def _query_groq(prompt: str) -> str:
    key = os.getenv("GROQ_API_KEY", "")
    if not key or key == "gsk_your_key_here":
        return ""
    try:
        from groq import Groq
        client = Groq(api_key=key, timeout=30, max_retries=0)
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=512,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        import sys; print(f"[ai_kernel] Groq error: {e}", file=sys.stderr)
    return ""


def _ollama_running() -> bool:
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=0.5)
        return resp.status_code == 200
    except Exception:
        return False


def _query_ollama(prompt: str, timeout: float = 30) -> str:
    try:
        import requests
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception:
        pass
    return ""


def is_ai_available() -> bool:
    return _ollama_running()


def _query_ai(prompt: str, timeout: float = 30) -> str:
    result = _query_ollama(prompt, timeout=timeout)
    if result:
        return result
    result = _query_groq(prompt)
    if result:
        return result
    return ""


def _check_cache(key: str):
    cache = st.session_state.get("ai_cache", {})
    return cache.get(key)


def _set_cache(key: str, value: str):
    if "ai_cache" not in st.session_state:
        st.session_state.ai_cache = {}
    cache = st.session_state.ai_cache
    cache[key] = value
    if len(cache) > CACHE_SIZE:
        oldest = next(iter(cache))
        del cache[oldest]


def _get_emotion_labels(text: str) -> str:
    try:
        from emotion_classifier import classify_text as _ct
        return _ct(text)
    except Exception as _e:
        import sys; print(f"[ai_kernel] classifier error: {_e}", file=sys.stderr)
        return ""


def summarize_journal(raw_text: str, mode: str = "patient") -> str:
    if not raw_text.strip():
        return "No content to summarize."

    cache_key = f"journal_{mode}_{hash(raw_text) % 10**8}"
    cached = _check_cache(cache_key)
    if cached:
        return cached

    emotions = _get_emotion_labels(raw_text)
    emotion_hint = f"\nEmotions detected: {emotions}." if emotions else ""

    if mode == "clinical":
        prompt = (
            "You are Sentinel, a clinical documentation AI. Read this journal entry "
            "and write a brief clinical summary (2-4 sentences)."
            f"{emotion_hint}"
            " Use clinical tone, third person, past tense. Do not quote verbatim."
            f"\n\nJournal Entry:\n{raw_text}"
            f"\n\nClinical Summary:"
        )
    else:
        prompt = (
            "You are Sentinel, an emotionally intelligent assistant. Read this journal entry "
            "and write a brief, warm reflection (2-4 sentences)."
            f"{emotion_hint}"
            " Acknowledge and validate their feelings. No advice whatsoever — "
            "no suggestions, no 'try this', no 'consider that', no 'remember to', "
            "no coping techniques, no deep breaths. Zero prescription. Just sit with them."
            f"\n\nJournal Entry:\n{raw_text}"
            f"\n\nReflection:"
        )

    result = _query_ollama(prompt, timeout=15)
    if not result or _is_raw_echo(result, raw_text):
        result = _query_groq(prompt)
    if not result or _is_raw_echo(result, raw_text):
        result = _fallback_summary(raw_text, emotions, mode)

    _set_cache(cache_key, result)
    return result


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
    import re as _re
    out_words = set(_re.findall(r'\w+', cleaned))
    orig_words = set(_re.findall(r'\w+', orig_clean))
    if not orig_words:
        return False
    overlap = len(out_words & orig_words) / len(orig_words)
    return overlap > 0.85


def synthesize_clinical_notes(raw_notes: str) -> str:
    if not raw_notes.strip():
        return "No notes to synthesize."

    cache_key = f"notes_{hash(raw_notes) % 10**8}"
    cached = _check_cache(cache_key)
    if cached:
        return cached

    prompt = (
        "You are Sentinel. Convert these session notes into a structured clinical note "
        "with Observations, Assessment, and Plan sections. Use precise emotion language "
        "(from GoEmotions 28 labels) in the Assessment. Keep it professional but not cold.\n\n"
        f"Session Notes:\n{raw_notes}\n\nStructured Clinical Note:"
    )

    result = _query_ai(prompt)
    if not result:
        result = _fallback_synthesis(raw_notes)

    _set_cache(cache_key, result)
    return result


def assess_crisis_risk(text: str) -> dict:
    if not text.strip():
        return {"risk_score": 1, "reasoning": "No content to assess.", "triggered": False}

    if not _ollama_running():
        return _fallback_risk_assessment(text)

    prompt = (
        "You are Sentinel. Assess crisis risk in this journal entry. Use GoEmotions "
        "28-label emotion language in your reasoning (admiration, amusement, anger, annoyance, "
        "approval, caring, confusion, curiosity, desire, disappointment, disapproval, disgust, "
        "embarrassment, excitement, fear, gratitude, grief, joy, love, nervousness, optimism, "
        "pride, realization, relief, remorse, sadness, surprise, neutral).\n\n"
        f"Journal Entry:\n{text}\n\n"
        "Return ONLY a valid JSON object with two fields: "
        "\"risk_score\" (integer 1-10) and \"reasoning\" (string). "
        "Example: {\"risk_score\": 7, \"reasoning\": \"Fear and sadness detected with passive ideation.\"}"
    )

    raw = _query_ollama(prompt, timeout=15)
    if raw:
        import re, json as _json
        match = re.search(r'\{[^{}]*"risk_score"[^{}]*\}', raw, re.DOTALL)
        if match:
            try:
                result = _json.loads(match.group())
                if isinstance(result.get("risk_score"), (int, float)):
                    result["risk_score"] = int(result["risk_score"])
                    result["triggered"] = result["risk_score"] >= 8
                    return result
            except Exception:
                pass

    return _fallback_risk_assessment(text)


def _fallback_risk_assessment(text: str) -> dict:
    crisis_keywords = [
        "suicide", "kill myself", "end my life", "want to die", "not worth living",
        "self-harm", "hurt myself", "emergency", "can't take it", "overdose",
    ]
    high_keywords = [
        "panic", "hopeless", "desperate", "terrified", "screaming", "can't breathe",
        "alone", "scared", "anxiety", "afraid", "worthless", "numb",
    ]
    medium_keywords = [
        "sad", "worried", "tired", "stress", "overwhelmed", "frustrated",
        "angry", "upset", "crying", "lost",
    ]

    lower = text.lower()
    score = 1

    if any(kw in lower for kw in crisis_keywords):
        score = 10
    elif any(kw in lower for kw in high_keywords):
        score = 7
    elif any(kw in lower for kw in medium_keywords):
        score = 4

    return {
        "risk_score": score,
        "reasoning": f"Keyword-based fallback analysis. Score {score}/10.",
        "triggered": score >= 8,
    }


def _fallback_summary(text: str, emotions: str = "", mode: str = "patient") -> str:
    if not text.strip():
        return "No content to summarize."
    if mode == "clinical":
        return (
            "**Observations**: Patient reports emotional experiences "
            f"consistent with {emotions if emotions else 'mixed affect'}.\n\n"
            "**Assessment**: Emotional awareness present. Continue monitoring.\n\n"
            "**Plan**: Follow-up within standard interval."
        )
    if emotions:
        return f"Emotions detected: {emotions}. Brief entry noted."
    return "Brief entry noted. Monitor mood trends."


def _fallback_synthesis(text: str) -> str:
    return (
        "**Observations**: " + text[:200] + ("..." if len(text) > 200 else "") + "\n\n"
        "**Assessment**: Patient appears engaged in therapeutic process. "
        "Continue monitoring emotional trajectory.\n\n"
        "**Plan**: Follow-up session recommended within standard interval."
    )
