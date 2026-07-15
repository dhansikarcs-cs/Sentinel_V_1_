from sqlalchemy import Column, Integer, String, Text, ForeignKey

from app.core.database import Base


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    raw_content = Column(Text, default="")
    summary = Column(Text, default="")
    hmac = Column(String, default="")
    ai_source = Column(String, default="")
    emotions = Column(String, default="")
    timestamp = Column(String, nullable=False)
