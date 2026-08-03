from sqlalchemy import Column, ForeignKey, Integer, String

from app.core.database import Base
from app.core.encrypted_fields import EncryptedText


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    psychologist_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    raw_notes = Column(EncryptedText, default="")
    ai_synthesis = Column(EncryptedText, default="")
    timestamp = Column(String, nullable=False)
    approved_by = Column(String, default="")
    approved_at = Column(String, default="")
