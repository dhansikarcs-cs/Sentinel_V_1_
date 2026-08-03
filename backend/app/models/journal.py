from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index

from app.core.database import Base
from app.core.encrypted_fields import EncryptedText


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        Index("ix_journal_patient_username", "patient_username"),
        Index("ix_journal_timestamp", "timestamp"),
        Index("ix_journal_ai_source", "ai_source"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    raw_content = Column(EncryptedText, default="")
    summary = Column(EncryptedText, default="")
    clinical_summary = Column(EncryptedText, default="")
    hmac = Column(String, default="")
    ai_source = Column(String, default="")
    emotions = Column(String, default="")
    emotion_probabilities = Column(Text, default="")
    timestamp = Column(String, nullable=False)
    created_at = Column(String, default="")
    updated_at = Column(String, default="")
    deleted_at = Column(String, nullable=True, default=None)
    deleted_by = Column(String, nullable=True, default=None)
    version = Column(Integer, default=1, nullable=False)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
