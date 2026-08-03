from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.journal import JournalEntry
from app.repositories.base import BaseRepository


class JournalRepository(BaseRepository[JournalEntry]):
    def __init__(self, db: Session):
        super().__init__(JournalEntry, db)

    def get_by_patient(
        self,
        username: str,
        limit: int = 0,
        include_deleted: bool = False,
        emotion: str = "",
        ai_source: str = "",
        date_from: str = "",
        date_to: str = "",
    ) -> list[JournalEntry]:
        q = self.db.query(JournalEntry).filter(JournalEntry.patient_username == username)
        if not include_deleted:
            q = q.filter(JournalEntry.deleted_at.is_(None))
        if emotion:
            q = q.filter(JournalEntry.emotions.ilike(f"%{emotion}%"))
        if ai_source:
            q = q.filter(JournalEntry.ai_source == ai_source)
        if date_from:
            q = q.filter(JournalEntry.timestamp >= date_from)
        if date_to:
            q = q.filter(JournalEntry.timestamp <= date_to)
        q = q.order_by(JournalEntry.timestamp.desc())
        if limit:
            q = q.limit(limit)
        return q.all()

    def get_by_id(self, journal_id: int) -> Optional[JournalEntry]:
        return self.db.query(JournalEntry).filter(JournalEntry.id == journal_id).first()

    def get_recent_summaries(self, username: str, limit: int = 20) -> list[JournalEntry]:
        return self.get_by_patient(username, limit=limit)

    def soft_delete(self, journal_id: int, deleted_by: str = "") -> bool:
        entry = self.get_by_id(journal_id)
        if not entry or entry.deleted_at:
            return False
        entry.deleted_at = datetime.now(timezone.utc).isoformat()
        entry.deleted_by = deleted_by
        self.db.commit()
        return True

    def restore(self, journal_id: int) -> bool:
        entry = self.get_by_id(journal_id)
        if not entry or not entry.deleted_at:
            return False
        entry.deleted_at = None
        entry.deleted_by = None
        self.db.commit()
        return True

    def increment_version(self, journal_id: int) -> int:
        entry = self.get_by_id(journal_id)
        if not entry:
            return 0
        entry.version = (entry.version or 1) + 1
        entry.updated_at = datetime.now(timezone.utc).isoformat()
        self.db.commit()
        return entry.version
