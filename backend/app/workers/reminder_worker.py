import asyncio
import logging
from datetime import UTC, datetime

from app.core.database import SessionLocal
from app.models.journal import JournalEntry
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger("sentinel")

_REMINDER_CHECK_SECONDS = 60 * 30  # sweep every 30 minutes
_REMINDER_ACTIVE_FROM_HOUR = 8  # only queue reminders between 08:00 and 21:00
_REMINDER_ACTIVE_UNTIL_HOUR = 21

REMINDER_TITLE = "📅 Daily journal reminder"
REMINDER_MESSAGE = "Take 2 minutes to jot down how you're feeling today. Your clinician sees the summary."


def _sweep_reminders() -> None:
    db = SessionLocal()
    try:
        now = datetime.now()
        if not (_REMINDER_ACTIVE_FROM_HOUR <= now.hour < _REMINDER_ACTIVE_UNTIL_HOUR):
            return
        today = datetime.now(UTC).date().isoformat()
        patients = db.query(User).filter(User.role == "patient", User.deleted_at.is_(None)).all()
        for p in patients:
            journal_today = (
                db.query(JournalEntry)
                .filter(
                    JournalEntry.patient_username == p.username,
                    JournalEntry.timestamp >= today,
                    JournalEntry.deleted_at.is_(None),
                )
                .first()
            )
            if journal_today:
                continue
            reminder_sent_today = (
                db.query(Notification)
                .filter(
                    Notification.patient_username == p.username,
                    Notification.title == REMINDER_TITLE,
                    Notification.sent_at >= today,
                )
                .first()
            )
            if reminder_sent_today:
                continue
            db.add(
                Notification(
                    patient_username=p.username,
                    title=REMINDER_TITLE,
                    message=REMINDER_MESSAGE,
                    notification_type="reminder",
                    read=0,
                    sent_at=datetime.now(UTC).isoformat(),
                )
            )
            db.commit()
            logger.info("journal reminder queued for %s", p.username)
    except Exception:
        logger.exception("journal reminder sweep failed")
    finally:
        db.close()


async def reminder_loop() -> None:
    loop = asyncio.get_running_loop()
    while True:
        try:
            await loop.run_in_executor(None, _sweep_reminders)
        except Exception:
            logger.exception("journal reminder loop error")
        await asyncio.sleep(_REMINDER_CHECK_SECONDS)
