"""Text-biometric mismatch detection + WS broadcast."""

import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.audit import log_audit
from app.services.websocket_manager import manager

router = APIRouter(prefix="/discrepancy", tags=["discrepancy"])

POSITIVE_SET = {
    "great",
    "happy",
    "good",
    "wonderful",
    "amazing",
    "fantastic",
    "energetic",
    "refreshed",
    "joy",
    "love",
    "beautiful",
    "perfect",
    "cured",
    "better",
    "peaceful",
    "content",
    "grateful",
    "optimistic",
}
NEGATIVE_SET = {
    "anxious",
    "scared",
    "terrified",
    "panic",
    "fear",
    "afraid",
    "hopeless",
    "die",
    "kill",
    "suicide",
    "disappear",
    "worried",
    "can't",
    "cannot",
    "unbearable",
    "drowning",
    "alone",
    "numb",
    "struggling",
    "darkness",
    "terrible",
    "falling apart",
}
NEGATION_PREFIXES = {
    "not",
    "no",
    "never",
    "don't",
    "dont",
    "doesn't",
    "doesnt",
    "isn't",
    "isnt",
    "wasn't",
    "wasnt",
    "won't",
    "wont",
    "can't",
    "cant",
    "couldn't",
    "couldnt",
    "shouldn't",
    "shouldnt",
    "wouldn't",
    "wouldnt",
    "hardly",
    "barely",
    "neither",
    "nor",
}


def _strip_negated_words(text: str, keywords: set) -> set:
    """Return keywords after removing those preceded by a negation prefix."""
    words = text.split()
    negated = set()
    i = 0
    while i < len(words):
        if words[i] in NEGATION_PREFIXES and i + 1 < len(words):
            for j in range(i + 1, min(i + 4, len(words))):
                candidate = words[j].rstrip(".,!?;:")
                if candidate in keywords:
                    negated.add(candidate)
            i += 2
        else:
            i += 1
    return keywords - negated


class DiscrepancyRequest(BaseModel):
    journal_text: str
    bpm: int
    hrv: int


class DiscrepancyResponse(BaseModel):
    discrepancy_detected: bool
    text_sentiment: str
    biometric_state: str
    processing_ms: float
    alert_broadcasted: bool


def _detect(text: str, bpm: int, hrv: int) -> tuple:
    t0 = time.perf_counter()
    lower = text.lower().strip()

    effective_pos = _strip_negated_words(lower, POSITIVE_SET)
    effective_neg = _strip_negated_words(lower, NEGATIVE_SET)
    has_pos = any(w in lower for w in effective_pos)
    has_neg = any(w in lower for w in effective_neg)

    if has_pos and not has_neg:
        sentiment = "positive"
    elif has_neg and not has_pos:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    high_stress = bpm >= 110 and hrv <= 25
    low_stress = bpm <= 80 and hrv >= 55

    if high_stress:
        bio_state = "high_stress"
    elif low_stress:
        bio_state = "low_stress"
    else:
        bio_state = "moderate"

    discrepancy = (
        (sentiment == "positive" and high_stress)
        or (sentiment == "negative" and low_stress)
        or (sentiment == "neutral" and high_stress)
    )

    elapsed = (time.perf_counter() - t0) * 1000
    return discrepancy, sentiment, bio_state, elapsed


@router.post("/check", response_model=DiscrepancyResponse)
async def check_discrepancy(
    req: DiscrepancyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detected, sentiment, bio_state, ms = _detect(req.journal_text, req.bpm, req.hrv)
    alert_sent = False

    if detected:
        await manager.broadcast_to_psych(
            "discrepancy_alert",
            {
                "patient": user.username,
                "sentiment": sentiment,
                "bpm": req.bpm,
                "hrv": req.hrv,
                "biometric_state": bio_state,
                "processing_ms": round(ms, 2),
            },
        )
        alert_sent = True

    log_audit(
        "discrepancy_check",
        user=user.username,
        role=user.role,
        severity="HIGH" if detected else "INFO",
        status="success",
        details=f"sentiment={sentiment}, bio={bio_state}, detected={detected}",
        db=db,
    )

    return DiscrepancyResponse(
        discrepancy_detected=detected,
        text_sentiment=sentiment,
        biometric_state=bio_state,
        processing_ms=round(ms, 2),
        alert_broadcasted=alert_sent,
    )
