import requests
import json
import os
import streamlit as st

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"
CACHE_SIZE = 20
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-70b-8192"


def _query_groq(prompt: str) -> str:
    key = os.getenv("GROQ_API_KEY", "")
    if not key or key == "gsk_your_key_here":
        return ""
    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 512,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return ""


def _query_ollama(prompt: str) -> str:
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except (requests.ConnectionError, requests.Timeout, json.JSONDecodeError):
        pass
    return ""


def _query_ai(prompt: str) -> str:
    result = _query_groq(prompt)
    if result:
        return result
    result = _query_ollama(prompt)
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
