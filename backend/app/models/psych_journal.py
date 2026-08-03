from sqlalchemy import Column, Integer, String, Text

from app.core.database import Base
from app.core.encrypted_fields import EncryptedText


class PsychJournalEntry(Base):
    __tablename__ = "psych_journal_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    psychologist_username = Column(String, nullable=False)
    raw_content = Column(EncryptedText, default="")
    summary = Column(EncryptedText, default="")
    hmac = Column(String, default="")
    ai_source = Column(String, default="")
    emotions = Column(String, default="")
    timestamp = Column(String, nullable=False)
