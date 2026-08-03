from sqlalchemy import Column, Float, ForeignKey, Index, Integer, String, Text

from app.core.database import Base


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        Index("ix_risk_journal_id", "journal_id"),
        Index("ix_risk_patient_username", "patient_username"),
        Index("ix_risk_score", "risk_score"),
        Index("ix_risk_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    journal_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    emotion_result_id = Column(Integer, ForeignKey("emotion_results.id"), nullable=True)
    sensor_reading_id = Column(Integer, ForeignKey("sensor_readings.id"), nullable=True)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)

    risk_score = Column(Integer, default=0)
    triggered = Column(Integer, default=0)
    confidence = Column(Float, default=0.0)
    explanation = Column(Text, default="")
    algorithm_version = Column(String, default="1.0.0")
    created_at = Column(String, nullable=False)
