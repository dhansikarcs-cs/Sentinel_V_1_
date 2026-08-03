import contextlib
import json
import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.booking import Booking, PsychAvailability
from app.models.crisis import CrisisState
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.ring import RingSensorLog
from app.models.user import User
from app.services.ai_service import (
    _query_ai,
    synthesize_clinical_notes,
)
from app.services.audit import log_audit
from app.services.patient_context import (
    build_triage_prompt,
    derive_triage_tier,
    recent_patient_context,
    triage_priority_score,
)

router = APIRouter(prefix="/agents", tags=["agents"])

_triage_cache: dict[str, tuple[float, dict]] = {}
TRIAGE_CACHE_TTL = 300  # 5 minutes

SLOT_SUGGESTION_PROMPT_V1 = """Patient "{patient_username}" has {bookings} pending booking(s).
Proposed slots: {slots}.

Give a priority assessment ("low"/"medium"/"high") and urgency score (1-10).
Return ONLY valid JSON with keys: priority (str), urgency_score (int), reasoning (str)."""

DRAFT_FOLLOWUP_PROMPT_V1 = """Patient "{patient_username}" wrote:
"{recent_text}"

Suggest follow-up tasks (max 3) based on this journal. Each task should have a title and description.
Return ONLY valid JSON with keys:
- tasks: list of {{title: str, description: str}}
- priority: "low"/"medium"/"high"
- urgency_score: int 1-10
- reasoning: str"""

PRE_SESSION_BRIEF_PROMPT_V1 = """Pre-session brief for patient "{patient_username}".

Recent journal excerpts: "{recent_texts}"
Recent moods: {recent_moods}
Mood trend: {mood_trend}
Avg BPM: {avg_bpm}
Completed tasks: {completed_followups}
Pending tasks: {pending_followups}

Return ONLY valid JSON with: concerns (list of str), summary (str), suggested_focus (str).
Keep summary to 2-3 sentences suitable for a psychologist's pre-session review."""

RING_VITALS_RISK_PROMPT_V1 = """Vitals risk assessment for patient:
Heart rate: {bpm} BPM
Stress: {stress}
Sleep: {sleep}h
SpO2: {spo2}%

Return ONLY valid JSON with: risk ("low"/"medium"/"high"), flags (list of str), recommendation (str)."""

CRISIS_DEBRIEF_PROMPT_V1 = """Crisis debrief for patient "{patient_username}".

Trigger text: "{trigger}"
Heart rate: {bpm} BPM
Stress: {stress}

Provide a structured debrief for the psychologist. Return ONLY valid JSON with:
- severity: "low"/"moderate"/"high"/"critical"
- likely_triggers: list of str
- recommended_interventions: list of str
- debrief_note: str (1-2 paragraph clinical note)
- follow_up_plan: str"""


class TriageSummaryRequest(BaseModel):
    patient_username: str


class SlotSuggestionRequest(BaseModel):
    patient_username: str


class DraftFollowupRequest(BaseModel):
    patient_username: str


class JournalToNoteRequest(BaseModel):
    patient_username: str
    journal_text: str
    clinical_summary: str = ""


class PreSessionBriefRequest(BaseModel):
    patient_username: str


@router.post("/triage-summary")
def triage_summary(
    req: TriageSummaryRequest, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    cache_key = f"triage:{req.patient_username}"
    cached = _triage_cache.get(cache_key)
    if cached and (time.time() - cached[0]) < TRIAGE_CACHE_TTL:
        return cached[1]

    ctx = recent_patient_context(db, req.patient_username)
    recent_mood = ctx.recent_mood_label
    bpm = ctx.latest_bpm
    stress = ctx.latest_stress

    prompt = build_triage_prompt(ctx)

    ai = _query_ai(prompt)
    data = {}
    try:
        data = json.loads(ai)
        score = data.get("score", 1)
        reasons = data.get("reasons", [])
        priority = data.get("priority", "low")
    except Exception:
        score = 1
        reasons = ["AI unavailable, used rule fallback"]
        priority = "low"

    crisis_state = db.query(CrisisState).first()
    crisis = bool(crisis_state and crisis_state.active and crisis_state.patient_username == req.patient_username)
    tier = derive_triage_tier(priority, crisis=crisis)

    log_audit(
        "agent_triage_summary",
        user=user.username,
        role=user.role,
        severity="INFO",
        status="success",
        resource=req.patient_username,
        details=f"score={score}, priority={priority}, tier={tier}",
        db=db,
    )

    result = {
        "patient": req.patient_username,
        "priority": priority,
        "urgency_score": score,
        "tier": tier,
        "priority_score": triage_priority_score(tier),
        "crisis": crisis,
        "suggestion": data.get("suggestion", f"Patient triaged at {priority} priority (score: {score}/10)."),
        "reasoning": "; ".join(reasons) if reasons else "No significant indicators detected.",
        "recent_mood": recent_mood,
        "bpm": bpm,
        "stress": stress,
        "prompt_version": "triage/v1",
    }
    _triage_cache[cache_key] = (time.time(), result)
    return result


@router.post("/suggest-slots")
def suggest_slots(
    req: SlotSuggestionRequest, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    now = datetime.now()
    available_dates = db.query(PsychAvailability).filter(PsychAvailability.psychologist_username == user.username).all()

    candidate_dates = []
    if available_dates:
        candidate_dates = sorted({a.date for a in available_dates})
    else:
        for day_offset in range(1, 16):
            d = now + timedelta(days=day_offset)
            if d.weekday() < 5:
                candidate_dates.append(d.strftime("%Y-%m-%d"))
            if len(candidate_dates) == 5:
                break

    slots = []
    for d in candidate_dates:
        for hour in [9, 10, 11, 14, 15]:
            slots.append({"label": f"{d} @ {hour}:00", "date": d, "time": f"{hour}:00"})

    today_str = now.strftime("%Y-%m-%d")
    future = [s for s in slots if s["date"] >= today_str]
    future.sort(key=lambda s: (s["date"], s["time"]))
    selected = future[:3]

    bookings = (
        db.query(Booking)
        .filter(Booking.patient_username == req.patient_username, Booking.status.in_(["Pending", "Proposed"]))
        .count()
    )

    prompt = SLOT_SUGGESTION_PROMPT_V1.format(
        patient_username=req.patient_username,
        bookings=bookings,
        slots=json.dumps([s["label"] for s in selected]),
    )

    ai = _query_ai(prompt)
    try:
        data = json.loads(ai)
    except Exception:
        data = {
            "priority": "medium" if bookings > 0 else "low",
            "urgency_score": min(bookings * 2, 10),
            "reasoning": f"Rule-based: {bookings} pending.",
        }

    return {
        "patient": req.patient_username,
        "suggested_slots": selected,
        "priority": data.get("priority", "low"),
        "urgency_score": data.get("urgency_score", 0),
        "workload": {"pending_bookings": bookings},
        "reasoning": data.get("reasoning", f"Suggested {len(selected)} slots."),
        "prompt_version": "slot_suggestion/v1",
    }


@router.post("/draft-followup")
def draft_followup(
    req: DraftFollowupRequest, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    ctx = recent_patient_context(db, req.patient_username, journal_limit=3, include_followups=True)
    existing = sum(1 for f in ctx.followups if f.status == "pending")

    recent_text = ctx.recent_text(500)

    prompt = DRAFT_FOLLOWUP_PROMPT_V1.format(
        patient_username=req.patient_username,
        recent_text=recent_text,
    )

    ai = _query_ai(prompt)
    try:
        data = json.loads(ai)
    except Exception:
        data = {
            "tasks": [{"title": "Daily Reflection", "description": "Write three things you're grateful for today."}],
            "priority": "medium" if existing > 0 else "low",
            "urgency_score": 3,
            "reasoning": "AI unavailable, used generic suggestion.",
        }

    return {
        "patient": req.patient_username,
        "tasks": data.get("tasks", []),
        "priority": data.get("priority", "low"),
        "urgency_score": data.get("urgency_score", 0),
        "pending_count": existing,
        "reasoning": data.get("reasoning", ""),
        "prompt_version": "draft_followup/v1",
    }


@router.post("/journal-to-note")
def journal_to_note(
    req: JournalToNoteRequest, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    combined = req.journal_text + ("\n\nClinical context: " + req.clinical_summary if req.clinical_summary else "")
    note_text = synthesize_clinical_notes(combined)

    text = req.journal_text.lower()
    themes = set()
    if any(kw in text for kw in ["anxious", "scared", "panic", "fear"]):
        themes.add("anxiety")
    if any(kw in text for kw in ["sad", "depressed", "hopeless", "numb"]):
        themes.add("depression")
    if any(kw in text for kw in ["sleep", "insomnia", "tired"]):
        themes.add("sleep disturbance")
    if any(kw in text for kw in ["angry", "frustrated", "irritated"]):
        themes.add("irritability")
    if any(kw in text for kw in ["friend", "family", "alone", "isolated"]):
        themes.add("social difficulty")
    if any(kw in text for kw in ["work", "school", "stress", "pressure"]):
        themes.add("occupational stress")
    if not themes:
        themes.add("general check-in")

    return {
        "patient": req.patient_username,
        "note": note_text,
        "themes": sorted(themes),
    }


@router.post("/pre-session-brief")
def pre_session_brief(
    req: PreSessionBriefRequest, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    return _build_pre_session_brief(db, req.patient_username)


@router.get("/pre-session-brief/{username}")
def get_pre_session_brief(
    username: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    return _build_pre_session_brief(db, username)


def _build_pre_session_brief(db: Session, username: str) -> dict:
    ctx = recent_patient_context(db, username, journal_limit=10, mood_limit=14, ring_limit=7, include_followups=True)
    journals = ctx.journals
    moods = ctx.moods
    followups = ctx.followups
    ring_data = ctx.ring_logs

    mood_trend = "stable"
    if len(moods) >= 2:
        recent = [m for m in moods[:7] if m.label in ("good", "great", "okay")]
        older = [m for m in moods[7:14] if m.label in ("good", "great", "okay")]
        if len(recent) < len(older):
            mood_trend = "declining"
        elif len(recent) > len(older):
            mood_trend = "improving"

    completed_followups = sum(1 for f in followups if f.status == "completed")
    pending_followups = sum(1 for f in followups if f.status == "pending")
    total_journals = len(journals)
    bpm_values = [r.bpm for r in ring_data if r.bpm]
    avg_bpm = round(sum(bpm_values) / max(len(bpm_values), 1))

    recent_texts = " ".join(j.raw_content[:200] for j in journals[:3]) if journals else "No entries"
    recent_moods = ", ".join(m.label for m in moods[:5]) if moods else "None"

    prompt = PRE_SESSION_BRIEF_PROMPT_V1.format(
        patient_username=username,
        recent_texts=recent_texts,
        recent_moods=recent_moods,
        mood_trend=mood_trend,
        avg_bpm=avg_bpm,
        completed_followups=completed_followups,
        pending_followups=pending_followups,
    )

    ai = _query_ai(prompt)
    try:
        data = json.loads(ai)
    except Exception:
        data = {}

    concerns = data.get("concerns", [])
    if mood_trend == "declining":
        concerns.append("Mood declining over past 2 weeks")
    if pending_followups > 3:
        concerns.append(f"{pending_followups} pending follow-ups")
    if avg_bpm > 90:
        concerns.append(f"Elevated heart rate ({avg_bpm} BPM)")
    if total_journals < 3:
        concerns.append("Low journal engagement")

    return {
        "patient": username,
        "mood_trend": mood_trend,
        "total_journals": total_journals,
        "completed_followups": completed_followups,
        "pending_followups": pending_followups,
        "avg_bpm": avg_bpm,
        "concerns": list(set(concerns)),
        "summary": data.get("summary", ""),
        "suggested_focus": data.get("suggested_focus", ""),
        "prompt_version": "pre_session_brief/v1",
    }


@router.post("/compliance-radar")
def compliance_radar(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    patients = db.query(User).filter(User.assigned_psych == user.username, User.role == "patient").all()
    results = []
    for p in patients:
        journals_7d = (
            db.query(JournalEntry)
            .filter(
                JournalEntry.patient_username == p.username,
                JournalEntry.timestamp >= (datetime.now(UTC) - timedelta(days=7)).isoformat(),
            )
            .count()
        )
        moods_7d = (
            db.query(MoodLog)
            .filter(
                MoodLog.patient_username == p.username,
                MoodLog.timestamp >= (datetime.now(UTC) - timedelta(days=7)).isoformat(),
            )
            .count()
        )
        ring_7d = (
            db.query(RingSensorLog)
            .filter(
                RingSensorLog.patient_username == p.username,
                RingSensorLog.logged_at >= (datetime.now(UTC) - timedelta(days=7)).isoformat(),
            )
            .count()
        )

        engagement = "high"
        if journals_7d == 0 and moods_7d == 0:
            engagement = "none"
        elif journals_7d < 2 or moods_7d < 2:
            engagement = "low"

        results.append(
            {
                "patient": p.username,
                "journals_7d": journals_7d,
                "moods_7d": moods_7d,
                "ring_readings_7d": ring_7d,
                "engagement": engagement,
                "flagged": engagement in ("low", "none"),
            }
        )
    return {"patients": sorted(results, key=lambda r: r["engagement"] != "none")}


@router.post("/silent-period-watch")
def silent_period_watch(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    patients = db.query(User).filter(User.assigned_psych == user.username, User.role == "patient").all()
    now = datetime.now(UTC)
    alerts = []
    for p in patients:
        last_journal = (
            db.query(JournalEntry)
            .filter(JournalEntry.patient_username == p.username)
            .order_by(JournalEntry.timestamp.desc())
            .first()
        )
        last_mood = (
            db.query(MoodLog).filter(MoodLog.patient_username == p.username).order_by(MoodLog.timestamp.desc()).first()
        )

        last_activity = None
        if last_journal:
            with contextlib.suppress(Exception):
                last_activity = datetime.fromisoformat(last_journal.timestamp)
        if last_mood:
            try:
                mood_ts = datetime.fromisoformat(last_mood.timestamp)
                if not last_activity or mood_ts > last_activity:
                    last_activity = mood_ts
            except Exception:
                pass

        if last_activity:
            hours_since = (now - last_activity).total_seconds() / 3600
            if hours_since > 72:
                alerts.append(
                    {
                        "patient": p.username,
                        "hours_since": round(hours_since),
                        "severity": "high",
                        "message": f"No activity for {round(hours_since)} hours",
                    }
                )
            elif hours_since > 48:
                alerts.append(
                    {
                        "patient": p.username,
                        "hours_since": round(hours_since),
                        "severity": "medium",
                        "message": f"No activity for {round(hours_since)} hours",
                    }
                )
        else:
            alerts.append(
                {
                    "patient": p.username,
                    "hours_since": 0,
                    "severity": "info",
                    "message": "No activity recorded yet",
                }
            )
    return {"alerts": sorted(alerts, key=lambda a: a["hours_since"], reverse=True)}


@router.post("/relapse-indicators")
def relapse_indicators(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    patients = db.query(User).filter(User.assigned_psych == user.username, User.role == "patient").all()
    results = []
    for p in patients:
        journals = (
            db.query(JournalEntry)
            .filter(JournalEntry.patient_username == p.username)
            .order_by(JournalEntry.timestamp.desc())
            .limit(10)
            .all()
        )
        moods = (
            db.query(MoodLog)
            .filter(MoodLog.patient_username == p.username)
            .order_by(MoodLog.timestamp.desc())
            .limit(14)
            .all()
        )

        indicators = []
        if journals:
            recent_text = " ".join(j.raw_content.lower() for j in journals[:3])
            if any(kw in recent_text for kw in ["relapse", "worse", "back to", "again"]):
                indicators.append("self-reported regression")
            if any(kw in recent_text for kw in ["stop", "quit", "skip", "avoid"]):
                indicators.append("treatment avoidance language")
            if any(kw in recent_text for kw in ["hopeless", "give up", "no point"]):
                indicators.append("hopelessness")

        if len(moods) >= 3:
            negative_count = sum(1 for m in moods[:7] if m.label in ("sad", "anxious", "irritable", "tired"))
            if negative_count >= 5:
                indicators.append("persistent negative mood")
            elif negative_count >= 3:
                indicators.append("increasing negative mood days")

        risk = "high" if len(indicators) >= 2 else "moderate" if len(indicators) >= 1 else "low"

        results.append(
            {
                "patient": p.username,
                "indicators": indicators,
                "indicator_count": len(indicators),
                "risk": risk,
            }
        )
    return {"patients": sorted(results, key=lambda r: r["indicator_count"], reverse=True)}


@router.post("/cross-patient-patterns")
def cross_patient_patterns(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    patients = db.query(User).filter(User.assigned_psych == user.username, User.role == "patient").all()
    total = len(patients)
    active_journal_today = 0
    active_mood_today = 0
    high_stress_count = 0
    low_engagement_count = 0

    today = datetime.now(UTC).strftime("%Y-%m-%d")

    for p in patients:
        j_today = (
            db.query(JournalEntry)
            .filter(JournalEntry.patient_username == p.username, JournalEntry.timestamp.like(f"{today}%"))
            .count()
        )
        m_today = db.query(MoodLog).filter(MoodLog.patient_username == p.username, MoodLog.date == today).count()
        ring_latest = (
            db.query(RingSensorLog)
            .filter(RingSensorLog.patient_username == p.username)
            .order_by(RingSensorLog.logged_at.desc())
            .first()
        )

        if j_today > 0:
            active_journal_today += 1
        if m_today > 0:
            active_mood_today += 1
        if ring_latest and ring_latest.stress and ring_latest.stress > 70:
            high_stress_count += 1
        if j_today == 0 and m_today == 0:
            low_engagement_count += 1

    return {
        "total_patients": total,
        "active_journal_today": active_journal_today,
        "active_mood_today": active_mood_today,
        "high_stress_count": high_stress_count,
        "low_engagement_count": low_engagement_count,
        "engagement_rate": round(active_journal_today / max(total, 1) * 100, 1),
    }


@router.post("/ring-vitals-risk")
def ring_vitals_risk(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    ring = (
        db.query(RingSensorLog)
        .filter(RingSensorLog.patient_username == user.username)
        .order_by(RingSensorLog.logged_at.desc())
        .first()
    )
    if not ring:
        return {"risk": "low", "flags": [], "bpm": 72, "stress": 35, "sleep": 7, "spo2": 98}

    bpm = ring.bpm or 72
    stress = ring.stress or 35
    sleep = ring.sleep_hours or 7
    spo2 = ring.spo2 or 98

    prompt = RING_VITALS_RISK_PROMPT_V1.format(bpm=bpm, stress=stress, sleep=sleep, spo2=spo2)

    ai = _query_ai(prompt)
    try:
        data = json.loads(ai)
    except Exception:
        data = {}

    flags = data.get("flags", [])
    if bpm > 100:
        flags.append("elevated heart rate")
    if stress > 70:
        flags.append("high stress")
    if sleep < 5:
        flags.append("low sleep")
    if spo2 < 92:
        flags.append("low oxygen saturation")
    flags = list(set(flags))

    risk = data.get("risk", "high" if len(flags) >= 2 else "medium" if len(flags) >= 1 else "low")

    return {
        "risk": risk,
        "flags": flags,
        "bpm": bpm,
        "stress": stress,
        "sleep": sleep,
        "spo2": spo2,
        "recommendation": data.get("recommendation", ""),
        "prompt_version": "ring_vitals_risk/v1",
    }


class CrisisDebriefRequest(BaseModel):
    patient_username: str
    trigger_text: str = ""
    vitals: dict = {}


@router.post("/crisis-debrief")
def crisis_debrief(
    req: CrisisDebriefRequest, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    ctx = recent_patient_context(db, req.patient_username, journal_limit=5, ring_limit=1)

    trigger = req.trigger_text or ctx.recent_text(300)
    bpm = ctx.latest_bpm
    stress = ctx.latest_stress

    prompt = CRISIS_DEBRIEF_PROMPT_V1.format(
        patient_username=req.patient_username,
        trigger=trigger,
        bpm=bpm,
        stress=stress,
    )

    ai = _query_ai(prompt)
    try:
        data = json.loads(ai)
    except Exception:
        data = {
            "severity": "moderate",
            "likely_triggers": ["Unable to analyze with AI"],
            "recommended_interventions": ["Monitor and follow up"],
            "debrief_note": "AI debrief unavailable.",
            "follow_up_plan": "Standard follow-up",
        }

    log_audit(
        "agent_crisis_debrief",
        user=user.username,
        role=user.role,
        severity="HIGH",
        status="success",
        resource=req.patient_username,
        db=db,
    )

    return {
        "patient": req.patient_username,
        "severity": data.get("severity", "moderate"),
        "likely_triggers": data.get("likely_triggers", []),
        "recommended_interventions": data.get("recommended_interventions", []),
        "debrief_note": data.get("debrief_note", ""),
        "follow_up_plan": data.get("follow_up_plan", ""),
        "ai_source": "ollama",
        "prompt_version": "crisis_debrief/v1",
    }
