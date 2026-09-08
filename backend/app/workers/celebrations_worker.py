import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.database import SessionLocal
from app.core.dates import dob_matches_today
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger("sentinel")

_SWEEP_SECONDS = 60 * 60 * 6  # every 6 hours

BIRTHDAY_TITLE = "🎂 Happy Birthday!"
_RECENT_WINDOW = timedelta(hours=30)  # avoid duplicates across sweep runs


def _already_sent_recently(db, username: str, title: str) -> bool:
    cutoff = (datetime.now(UTC) - _RECENT_WINDOW).isoformat()
    return (
        db.query(Notification)
        .filter(
            Notification.patient_username == username,
            Notification.title == title,
            Notification.sent_at >= cutoff,
        )
        .first()
        is not None
    )


def _user_today(p: User) -> date:
    tz = p.timezone or "UTC"
    try:
        return datetime.now(ZoneInfo(tz)).date()
    except Exception:
        return datetime.now(UTC).date()


def _sweep_celebrations(on: date | None = None) -> None:
    db = SessionLocal()
    try:
        patients = db.query(User).filter(User.role == "patient", User.deleted_at.is_(None)).all()
        for p in patients:
            today = on or _user_today(p)
            if dob_matches_today(p.dob, today) and not _already_sent_recently(db, p.username, BIRTHDAY_TITLE):
                db.add(
                    Notification(
                        patient_username=p.username,
                        title=BIRTHDAY_TITLE,
                        message="Wishing you a day full of little joys. 🧁 Your journal has a quick birthday card waiting for you!",
                        notification_type="celebration",
                        read=0,
                        sent_at=datetime.now(UTC).isoformat(),
                    )
                )
                db.commit()
    except Exception:
        logger.exception("celebration sweep failed")
    finally:
        db.close()


async def celebrations_loop() -> None:
    loop = asyncio.get_running_loop()
    while True:
        try:
            await loop.run_in_executor(None, _sweep_celebrations)
        except Exception:
            logger.exception("celebration loop error")
        await asyncio.sleep(_SWEEP_SECONDS)
