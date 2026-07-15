from sqlalchemy import Column, Integer, String, Text, ForeignKey

from app.core.database import Base


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    psychologist_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    raw_notes = Column(Text, default="")
    ai_synthesis = Column(Text, default="")
    timestamp = Column(String, nullable=False)
