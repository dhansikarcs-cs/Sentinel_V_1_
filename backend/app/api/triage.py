import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.ring import RingSensorLog
from app.models.triage import TriageEntry
from app.schemas.triage import TriageCreate, TriageUpdate, TriageResponse
from app.services.ai_service import _query_ai
from app.services.audit import log_audit

router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("", response_model=TriageResponse)
def create_triage_assessment(req: TriageCreate, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    journals = db.query(JournalEntry).filter(JournalEntry.patient_username == req.patient_username).order_by(JournalEntry.timestamp.desc()).limit(5).all()
    moods = db.query(MoodLog).filter(MoodLog.patient_username == req.patient_username).order_by(MoodLog.timestamp.desc()).limit(7).all()
    ring = db.query(RingSensorLog).filter(RingSensorLog.patient_username == req.patient_username).order_by(RingSensorLog.logged_at.desc()).first()

    recent_text = journals[0].raw_content[:500] if journals else "No recent journal entries"
    recent_mood = moods[0].label if moods else "unknown"
    bpm = ring.bpm if ring else 72
    stress = ring.stress if ring else 35

    prompt = f"""Triage urgency assessment for patient "{req.patient_username}".

Recent journal excerpt: "{recent_text}"
Recent mood label: {recent_mood}
Heart rate: {bpm} BPM
Stress: {stress}

Assess the urgency of this patient's situation on a scale of 1-10 (1=stable, 10=immediate crisis).
Return ONLY valid JSON with keys: score (int), priority ("low"/"medium"/"high"), reasons (list of str), suggestion (str)."""

    ai = _query_ai(prompt)
    try:
        import json
        data = json.loads(ai)
        score = data.get("score", 1)
        reasons = data.get("reasons", [])
        priority = data.get("priority", "low")
        suggestion = data.get("suggestion", "")
    except Exception:
        score = 1
        reasons = []
        priority = "low"
        suggestion = ""

    now = datetime.now(timezone.utc).isoformat()
    entry = TriageEntry(
        id=str(uuid.uuid4()),
        patient_username=req.patient_username,
        assessed_by=user.username,
        priority=priority,
        urgency_score=score,
        suggestion=suggestion,
        reasoning="; ".join(reasons) if reasons else "No significant indicators detected.",
        recent_mood=recent_mood,
        bpm=bpm,
        stress=stress,
        status="open",
        created_at=now,
        assessed_at=now,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    log_audit("triage_created", user=user.username, role=user.role, severity="INFO", status="success", resource=req.patient_username, details=f"priority={priority}, score={score}", db=db)
    return entry


@router.get("", response_model=list[TriageResponse])
def list_triage(user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    entries = db.query(TriageEntry).order_by(TriageEntry.created_at.desc()).limit(50).all()
    return entries


@router.get("/{patient_username}", response_model=list[TriageResponse])
def get_patient_triage(patient_username: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    entries = db.query(TriageEntry).filter(TriageEntry.patient_username == patient_username).order_by(TriageEntry.created_at.desc()).limit(20).all()
    return entries


@router.put("/{entry_id}", response_model=TriageResponse)
def update_triage_entry(entry_id: str, req: TriageUpdate, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    entry = db.query(TriageEntry).filter(TriageEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Triage entry not found")
    if req.status:
        entry.status = req.status
    if req.priority:
        entry.priority = req.priority
    db.commit()
    db.refresh(entry)
    return entry
