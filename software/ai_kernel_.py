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


def get_emotion_labels(text: str) -> str:
    try:
        from emotion_classifier import classify_text as _ct
        return _ct(text)
    except Exception as _e:
        import sys; print(f"[ai_kernel] classifier error: {_e}", file=sys.stderr)
        return ""


def summarize_journal(raw_text: str, mode: str = "patient") -> dict:
    if not raw_text.strip():
        return {"text": "No content to summarize.", "source": "", "emotions": ""}

    cache_key = f"journal_v2_{mode}_{hash(raw_text) % 10**8}"
    cached = _check_cache(cache_key)
    if cached:
        return cached

    emotions = get_emotion_labels(raw_text)
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

    text = _query_ollama(prompt, timeout=15)
    source = "ollama"
    if not text or _is_raw_echo(text, raw_text):
        text = _query_groq(prompt)
        source = "groq"
    if not text or _is_raw_echo(text, raw_text):
        text = _fallback_summary(raw_text, emotions, mode)
        source = "rule"

    output = {"text": text, "source": source, "emotions": emotions}
    _set_cache(cache_key, output)
    return output


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


def _compute_contributing_factors(text: str) -> dict:
    lower = text.lower()
    crisis_kw = ["suicide", "kill myself", "end my life", "want to die", "not worth living", "self-harm", "hurt myself", "emergency", "can't take it", "overdose"]
    high_kw = ["panic", "hopeless", "desperate", "terrified", "screaming", "can't breathe", "alone", "scared", "anxiety", "afraid", "worthless", "numb"]
    medium_kw = ["sad", "worried", "tired", "stress", "overwhelmed", "frustrated", "angry", "upset", "crying", "lost"]
    social_kw = ["friends", "family", "people", "nobody", "alone", "isolated", "no one", "lonely", "withdrew"]
    sleep_kw = ["sleep", "insomnia", "tired", "exhausted", "can't sleep", "wake up", "nightmare"]
    activity_kw = ["nothing", "didn't do", "stay in bed", "no energy", "can't", "avoid", "skipped"]

    return {
        "crisis_keywords": [kw for kw in crisis_kw if kw in lower],
        "high_risk_keywords": [kw for kw in high_kw if kw in lower],
        "moderate_keywords": [kw for kw in medium_kw if kw in lower],
        "social_withdrawal": sum(1 for kw in social_kw if kw in lower),
        "sleep_disturbance": sum(1 for kw in sleep_kw if kw in lower),
        "activity_decline": sum(1 for kw in activity_kw if kw in lower),
    }


def assess_crisis_risk(text: str) -> dict:
    if not text.strip():
        return {"risk_score": 1, "reasoning": "No content to assess.", "triggered": False, "contributing_factors": {}}

    factors = _compute_contributing_factors(text)

    if not _ollama_running():
        return _fallback_risk_assessment(text, factors)

    prompt = (
        "You are Sentinel. Assess crisis risk in this journal entry. Use GoEmotions "
        "28-label emotion language in your reasoning (admiration, amusement, anger, annoyance, "
        "approval, caring, confusion, curiosity, desire, disappointment, disapproval, disgust, "
        "embarrassment, excitement, fear, gratitude, grief, joy, love, nervousness, optimism, "
        "pride, realization, relief, remorse, sadness, surprise, neutral).\n\n"
        f"Journal Entry:\n{text}\n\n"
        "Return ONLY a valid JSON object with three fields: "
        "\"risk_score\" (integer 1-10), \"reasoning\" (string explaining why in clinical terms), "
        "and \"contributing_factors\" (object with keys like sentiment, emotions_detected, key_triggers). "
        "Example: {\"risk_score\": 7, \"reasoning\": \"Fear and sadness detected with passive ideation. Social withdrawal and sleep disturbance present.\", \"contributing_factors\": {\"sentiment\": \"negative\", \"emotions_detected\": [\"fear\", \"sadness\"], \"key_triggers\": [\"hopelessness\", \"social_isolation\"]}}"
    )

    raw = _query_ollama(prompt, timeout=15)
    if raw:
        import re, json as _json
        match = re.search(r'\{[^{}]*"risk_score"[^{}]*"reasoning"[^{}]*\}', raw, re.DOTALL)
        if match:
            try:
                result = _json.loads(match.group())
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
    crisis_keywords = factors.get("crisis_keywords", [])
    high_keywords = factors.get("high_risk_keywords", [])
    medium_keywords = factors.get("moderate_keywords", [])
    social = factors.get("social_withdrawal", 0)
    sleep = factors.get("sleep_disturbance", 0)
    activity = factors.get("activity_decline", 0)

    score = 1
    if crisis_keywords:
        score = 10
    elif high_keywords:
        score = 7
    elif medium_keywords:
        score = 4
    if social >= 2 or sleep >= 2 or activity >= 2:
        score = max(score, 5)

    factor_lines = []
    if crisis_keywords:
        factor_lines.append(f"CRISIS keywords detected: {', '.join(crisis_keywords)}")
    if high_keywords:
        factor_lines.append(f"High-risk indicators: {', '.join(high_keywords[:3])}")
    if medium_keywords:
        factor_lines.append(f"Moderate concerns: {', '.join(medium_keywords[:3])}")
    if social >= 2:
        factor_lines.append(f"Social withdrawal signals ({social}x)")
    if sleep >= 2:
        factor_lines.append(f"Sleep disturbance signals ({sleep}x)")
    if activity >= 2:
        factor_lines.append(f"Activity decline signals ({activity}x)")
    reasoning = "; ".join(factor_lines) if factor_lines else "No significant risk indicators detected."

    return {
        "risk_score": score,
        "reasoning": f"Keyword-based analysis. Score {score}/10. {reasoning}",
        "triggered": score >= 8,
        "contributing_factors": factors,
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
