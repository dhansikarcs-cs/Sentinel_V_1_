"""Text-biometric mismatch detection + WS broadcast."""

import re
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
    "hopeful",
    "well",
    "calm",
    "warm",
    "proud",
    "laugh",
    "laughing",
    "laughed",
    "smile",
    "smiling",
    "smiled",
    "progress",
    "strong",
    "win",
}
# Clinically-relevant depression/anxiety vocabulary. Tokens with a space are
# matched as exact phrases; single tokens are matched at word boundaries.
NEGATIVE_SET = {
    "anxious",
    "scared",
    "terrified",
    "panic",
    "fear",
    "afraid",
    "hopeless",
    "die",
    "killing",
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
    "nothing",
    # Depression symptom language
    "sad",
    "depressed",
    "worthless",
    "guilt",
    "guilty",
    "burden",
    "heaviness",
    "cried",
    "crying",
    "tears",
    "ruminating",
    "rumination",
    "empty",
    "emptiness",
    "helpless",
    "despair",
    "miserable",
    "misery",
    "isolated",
    "lonely",
    "apathetic",
    "overwhelmed",
    "exhausted",
    "stuck",
    "broken",
    "defeated",
    "trapped",
    "agonizing",
    "pain",
    "canceled",
    "cancelled",
    "give up",
    "giving up",
    "break down",
    "breaking down",
    "sleep forever",
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
    "didn't",
    "didnt",
    "hardly",
    "barely",
    "neither",
    "nor",
    "nothing",
    "nobody",
    "none",
    "without",
}
# Trailing negators: "joy anymore" => joy is negated by what follows it.
NEGATION_SUFFIXES = {"anymore"}
# "can't stop crying" / "can't stop laughing": the negator feeds into an
# intensifier, so it must not flip the emotion that comes after it.
IDIOM_INTENSIFIERS = {"stop", "help", "keep"}
NEGATION_WINDOW = 3
_TOKEN_RE = re.compile(r"[a-z']+")
_MULTIWORD_NEGATIVE = {w for w in NEGATIVE_SET if " " in w}


def _tokenize(lower: str) -> list[str]:
    return _TOKEN_RE.findall(lower)


def _negation_scope(tokens: list[str]) -> tuple[list[bool], list[bool]]:
    """Return (prefix_negated, suffix_negated) masks.

    Prefix negators ("not", "never", "nothing" ...) reach up to
    NEGATION_WINDOW tokens ahead, but a prefix feeding straight into an
    intensifier ("stop"/"help"/"keep") is an intensifying idiom and stops.
    Trailing negators ("anymore") reach up to NEGATION_WINDOW tokens back.
    """
    n = len(tokens)
    prefix_negated = [False] * n
    suffix_negated = [False] * n
    for i, w in enumerate(tokens):
        if w in NEGATION_PREFIXES:
            for j in range(i + 1, min(n, i + 1 + NEGATION_WINDOW)):
                if j == i + 1 and tokens[j] in IDIOM_INTENSIFIERS:
                    break  # "can't stop X": idiom, not a flip
                prefix_negated[j] = True
    for i, w in enumerate(tokens):
        if w in NEGATION_SUFFIXES:
            for j in range(max(0, i - NEGATION_WINDOW), i):
                suffix_negated[j] = True
    return prefix_negated, suffix_negated


def _effective_sentiment(lower: str) -> tuple[set[str], set[str]]:
    """Return (positive_hits, negative_hits) with polarity-aware negation.

    - A negated positive keyword flips to a negative signal ("not happy",
      "no joy anymore").
    - A prefix-negated negative keyword is neutralized ("not terrible");
      a suffix-negated one ("anymore") still counts — "I can't handle this
      anymore" stays negative.
    - Negation words themselves ("can't", "nothing") count as negative
      signals unless they head an intensifying idiom.
    - Multi-word phrases are matched as exact substrings.
    """
    tokens = _tokenize(lower)
    prefix_negated, suffix_negated = _negation_scope(tokens)

    pos_hits: set[str] = set()
    neg_hits: set[str] = set()

    for i, w in enumerate(tokens):
        # "can't stop crying"/"can't stop laughing": the negator heads an
        # intensifier, so the emotion word after it carries the signal and
        # the negator itself must not be double-counted.
        idiom_headed = (
            w in {"can't", "cannot", "cant", "couldn't", "couldnt", "won't", "wont"}
            and i + 1 < len(tokens)
            and tokens[i + 1] in IDIOM_INTENSIFIERS
        )
        if w in POSITIVE_SET:
            if prefix_negated[i] or suffix_negated[i]:
                neg_hits.add(w)
            else:
                pos_hits.add(w)
        elif not idiom_headed and (
            w in {"nothing", "nobody", "none"} or w in NEGATIVE_SET and not prefix_negated[i]
        ):
            neg_hits.add(w)

    for phrase in _MULTIWORD_NEGATIVE:
        if phrase in lower:
            neg_hits.add(phrase)

    return pos_hits, neg_hits


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

    effective_pos, effective_neg = _effective_sentiment(lower)
    has_pos = bool(effective_pos)
    has_neg = bool(effective_neg)

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
