import json
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.api_response import ok
from app.core.database import get_db
from app.core.dates import dob_matches_today
from app.core.dependencies import get_current_user, require_role
from app.core.idempotency import idempotency_store
from app.core.input_validator import validate_journal_content
from app.core.pagination import paginate
from app.events import get_event_bus
from app.models.journal import JournalEntry
from app.models.user import User
from app.repositories import JournalRepository
from app.schemas.journal import JournalCreate, JournalResponse
from app.services.ai_service import synthesize_clinical_notes
from app.workers.ai_worker import analyze_journal_background

router = APIRouter(prefix="/journal", tags=["journal"])


@router.post("", response_model=JournalResponse)
def create_journal(
    entry: JournalCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
    idempotency_key: str = Header(default=""),
):
    validate_journal_content(entry.raw_content)
    if idempotency_key:
        cached = idempotency_store.check(idempotency_key)
        if cached:
            existing = db.query(JournalEntry).filter(JournalEntry.id == cached.get("journal_id")).first()
            if existing:
                return existing

    journal = JournalEntry(
        patient_username=user.username,
        raw_content=entry.raw_content,
        summary="",
        clinical_summary="",
        ai_source="pending",
        emotions="",
        checkin_data=json.dumps([a.model_dump() for a in entry.checkin], ensure_ascii=False),
        timestamp=datetime.now(UTC).isoformat(),
        created_at=datetime.now(UTC).isoformat(),
        version=1,
    )
    db.add(journal)
    db.commit()
    db.refresh(journal)

    if idempotency_key:
        idempotency_store.store(idempotency_key, {"journal_id": journal.id})

    get_event_bus().emit(
        "journal:submitted",
        journal_id=journal.id,
        patient_username=user.username,
        raw_content=entry.raw_content,
        timestamp=journal.timestamp,
    )

    if user.assigned_psych:
        psych = db.query(User).filter(User.username == user.assigned_psych, User.role == "psychologist").first()
        if psych:
            from app.services.notify import create_notification

            create_notification(
                db,
                patient_username=user.username,
                recipient_username=psych.username,
                title="📝 New journal entry",
                message=f"{user.name or user.username} just wrote a new journal entry — the AI summary will be ready shortly.",
                notification_type="info",
            )

    background_tasks.add_task(
        analyze_journal_background,
        journal_id=journal.id,
        raw_content=entry.raw_content,
        patient_username=user.username,
    )

    return journal


@router.get("")
def get_journals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    emotion: str = Query(default=""),
    ai_source: str = Query(default=""),
    date_from: str = Query(default=""),
    date_to: str = Query(default=""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = JournalRepository(db)
    items = repo.get_by_patient(
        user.username,
        emotion=emotion,
        ai_source=ai_source,
        date_from=date_from,
        date_to=date_to,
    )
    return paginate(items, page=page, page_size=page_size)


@router.get("/prompts")
def get_journal_prompts(user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    today = _user_local_date(user)
    prompts: list[dict] = []

    if dob_matches_today(user.dob, today):
        prompts.append(
            {
                "key": "birthday",
                "emoji": "🎂",
                "title": "It's your birthday!",
                "question": "How is your special day going so far?",
                "options": ["Treating myself 🍰", "Time with people I love", "Quiet, low-key day", "Nothing planned, all good"],
            }
        )

    if _low_mood_logged_today(db, user.username, today):
        prompts.append(_low_mood_card())
    elif today.weekday() >= 5:
        prompts.append(_weekly_card(today))
    elif today.toordinal() % 2 == 0:
        prompts.append(_daily_card(today))

    return {"prompts": prompts[:2]}


LOW_MOOD_LABELS = {"bad", "awful", "terrible"}

WEEKEND_CARDS = [
    {
        "emoji": "🌤️",
        "title": "Weekend weather check",
        "question": "What's the highlight of your weekend so far?",
        "options": ["Slow morning ☕", "Time with someone I love", "Something new I tried", "A good meal 🍛", "Just recharging"],
    },
    {
        "emoji": "🪁",
        "title": "Weekend reset",
        "question": "How does today feel compared to your week?",
        "options": ["Lighter 😌", "Same as always", "A bit restless", "Sleepier 😴", "Busier than I'd like"],
    },
]

DAILY_CARDS = [
    {
        "emoji": "🌼",
        "title": "Tiny wins",
        "question": "What's one small thing that felt good today?",
        "options": ["The weather 🌤️", "A nice chat 💬", "Something I ate 🍲", "Time with myself 🧘", "Nothing yet"],
    },
    {
        "emoji": "🧩",
        "title": "What's on your mind",
        "question": "What's taking up space in your head today?",
        "options": ["Something I'm planning", "A person I keep thinking of", "Work or studies", "My health", "Nothing heavy — all good"],
    },
    {
        "emoji": "🍃",
        "title": "Present moment",
        "question": "What did today's calmest moment look like?",
        "options": ["A deep breath", "A few quiet minutes", "Talking with someone", "Being outdoors 🌳", "A coffee/tea break"],
    },
]


def _low_mood_card() -> dict:
    return {
        "key": "low-mood",
        "emoji": "🤗",
        "title": "You logged a rough day — checking in",
        "question": "What's closest to how you're feeling right now?",
        "options": ["Overwhelmed 😵", "Low but holding on", "Frustrated or angry", "Anxious", "Mostly just tired"],
    }


def _weekly_card(today) -> dict:
    card = WEEKEND_CARDS[today.toordinal() % len(WEEKEND_CARDS)]
    return {"key": "weekend", **card}


def _daily_card(today) -> dict:
    card = DAILY_CARDS[today.toordinal() % len(DAILY_CARDS)]
    return {"key": "curious", **card}


def _low_mood_logged_today(db: Session, username: str, day) -> bool:
    from app.models.mood import MoodLog

    existing = db.query(MoodLog).filter(MoodLog.patient_username == username, MoodLog.date == day.isoformat()).first()
    return existing is not None and (existing.label or "").lower() in LOW_MOOD_LABELS


def _user_local_date(user: User):
    from datetime import date, datetime
    from zoneinfo import ZoneInfo

    tz = user.timezone or "UTC"
    try:
        return datetime.now(ZoneInfo(tz)).date()
    except Exception:
        return date.today()


@router.get("/{username}", response_model=list[JournalResponse])
def get_patient_journals(
    username: str,
    emotion: str = Query(default=""),
    ai_source: str = Query(default=""),
    date_from: str = Query(default=""),
    date_to: str = Query(default=""),
    user: User = Depends(require_role("psychologist")),
    db: Session = Depends(get_db),
):
    repo = JournalRepository(db)
    journals = repo.get_by_patient(
        username,
        emotion=emotion,
        ai_source=ai_source,
        date_from=date_from,
        date_to=date_to,
    )
    get_event_bus().emit("journal:viewed", journal_id=0, viewer_username=user.username, patient_username=username)
    return journals


@router.get("/{username}/summaries")
def get_patient_summaries(
    username: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    repo = JournalRepository(db)
    entries = repo.get_recent_summaries(username, limit=20)
    get_event_bus().emit("journal:summaries_viewed", viewer_username=user.username, patient_username=username)
    return [
        {
            "id": e.id,
            "summary": e.clinical_summary or e.summary,
            "patient_summary": e.summary,
            "clinical_summary": e.clinical_summary or e.summary,
            "ai_source": e.ai_source,
            "emotions": e.emotions,
            "timestamp": e.timestamp,
        }
        for e in entries
    ]


@router.post("/{journal_id}/resummarize", response_model=JournalResponse)
def resummarize_journal(
    journal_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = JournalRepository(db)
    journal = repo.get_by_id(journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    if journal.patient_username != user.username and user.role != "psychologist":
        raise HTTPException(status_code=403, detail="Not authorized")

    background_tasks.add_task(
        analyze_journal_background,
        journal_id=journal.id,
        raw_content=journal.raw_content,
        patient_username=journal.patient_username,
    )
    return journal


@router.delete("/{journal_id}")
def delete_journal(journal_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = JournalRepository(db)
    journal = repo.get_by_id(journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    if journal.patient_username != user.username and user.role != "psychologist":
        raise HTTPException(status_code=403, detail="Not authorized")
    repo.soft_delete(journal_id, deleted_by=user.username)
    return ok(message="Journal deleted")


class SynthesizeNoteRequest(BaseModel):
    journal_text: str
    clinical_summary: str = ""


@router.post("/synthesize-note")
def synthesize_note(
    req: SynthesizeNoteRequest, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    combined = req.journal_text + ("\n\nClinical context: " + req.clinical_summary if req.clinical_summary else "")
    note = synthesize_clinical_notes(combined)
    get_event_bus().emit("clinical_note:synthesized", psychologist=user.username)
    return {"note": note}
