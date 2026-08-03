from sqlalchemy import Column, Integer, String

from app.core.database import Base
from app.core.encrypted_fields import EncryptedText


class TriageEntry(Base):
    __tablename__ = "triage_queue"
    id = Column(String, primary_key=True)
    patient_username = Column(String, nullable=False)
    assessed_by = Column(String, default="")
    priority = Column(String, default="low")
    urgency_score = Column(Integer, default=0)
    suggestion = Column(EncryptedText, default="")
    reasoning = Column(EncryptedText, default="")
    recent_mood = Column(String, default="")
    bpm = Column(Integer, default=0)
    stress = Column(Integer, default=0)
    status = Column(String, default="open")
    created_at = Column(String, default="")
    assessed_at = Column(String, default="")
