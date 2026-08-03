from sqlalchemy import Column, Integer, String, ForeignKey, Index

from app.core.database import Base


class MoodLog(Base):
    __tablename__ = "mood_log"
    __table_args__ = (
        Index("ix_mood_patient_username", "patient_username"),
        Index("ix_mood_date", "date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    date = Column(String, nullable=False)
    emoji = Column(String, nullable=False)
    label = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)
