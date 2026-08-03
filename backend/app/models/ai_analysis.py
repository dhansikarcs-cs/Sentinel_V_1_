from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, Index, CheckConstraint

from app.core.database import Base


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    __table_args__ = (
        Index("ix_ai_journal_id", "journal_id"),
        Index("ix_ai_patient_username", "patient_username"),
        Index("ix_ai_priority", "priority"),
        Index("ix_ai_created_at", "created_at"),
        CheckConstraint("priority IN ('low', 'medium', 'high')", name="ck_ai_priority"),
        CheckConstraint("provider IN ('rule', 'ollama', 'groq', 'pending')", name="ck_ai_provider"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    journal_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=False)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)

    summary_patient = Column(Text, default="")
    summary_clinical = Column(Text, default="")
    priority = Column(String, default="low")
    confidence = Column(Float, default=0.0)
    explanation = Column(Text, default="")
    provider = Column(String, default="rule")  # rule | ollama | groq
    model_version = Column(String, default="1.0.0")
    created_at = Column(String, nullable=False)
