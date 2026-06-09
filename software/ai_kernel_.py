import os
import streamlit as st

CACHE_SIZE = 20
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral"


def _query_groq(prompt: str) -> str:
    key = os.getenv("GROQ_API_KEY", "")
    if not key or key == "gsk_your_key_here":
        return ""
    try:
        from groq import Groq
        client = Groq(api_key=key, timeout=3, max_retries=0)
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


def _query_ollama(prompt: str, timeout: float = 3) -> str:
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


def _query_ai(prompt: str) -> str:
    result = _query_ollama(prompt)
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


def summarize_journal(raw_text: str) -> str:
    if not raw_text.strip():
        return "No content to summarize."

    cache_key = f"journal_{hash(raw_text) % 10**8}"
    cached = _check_cache(cache_key)
    if cached:
        return cached

    prompt = (
        "You are a clinical AI assistant. Summarize the following patient journal entry "
        "in a brief, emotionally neutral, professional tone suitable for a psychologist's review. "
        "Focus on emotional state, possible concerns, and wellbeing indicators.\n\n"
        f"Journal Entry:\n{raw_text}\n\nSummary:"
    )

    result = _query_ai(prompt)
    if not result:
        result = _fallback_summary(raw_text)

    _set_cache(cache_key, result)
    return result


def synthesize_clinical_notes(raw_notes: str) -> str:
    if not raw_notes.strip():
        return "No notes to synthesize."

    cache_key = f"notes_{hash(raw_notes) % 10**8}"
    cached = _check_cache(cache_key)
    if cached:
        return cached

    prompt = (
        "You are a clinical documentation specialist. Convert the following psychologist "
        "session notes into a structured, professional clinical note. Use clear sections "
        "for Observations, Assessment, and Plan.\n\n"
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
        "System Alert: Biometric sensors detect an elevated stress state. "
        "Analyze the following user journal entry for psychological sentiment, "
        "anxiety markers, or crisis triggers.\n\n"
        f"Journal Entry:\n{text}\n\n"
        "Return ONLY a valid JSON object with two fields: "
        "\"risk_score\" (integer 1-10) and \"reasoning\" (string). "
        "Example: {\"risk_score\": 7, \"reasoning\": \"High anxiety markers detected.\"}"
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


def _fallback_summary(text: str) -> str:
    lines = [l for l in text.split(". ") if l]
    if len(lines) > 2:
        return (
            "Patient expresses multiple emotional themes. "
            f"Key topics include: {'; '.join(l.strip()[:60] for l in lines[:3])}. "
            "Recommended: monitor mood trends and consider follow-up discussion."
        )
    return "Patient shared emotional content. Further exploration recommended during next session."


def _fallback_synthesis(text: str) -> str:
    return (
        "**Observations**: " + text[:200] + ("..." if len(text) > 200 else "") + "\n\n"
        "**Assessment**: Patient appears engaged in therapeutic process. "
        "Continue monitoring emotional trajectory.\n\n"
        "**Plan**: Follow-up session recommended within standard interval."
    )
