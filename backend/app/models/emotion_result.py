from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, Index

from app.core.database import Base


class EmotionResult(Base):
    __tablename__ = "emotion_results"
    __table_args__ = (
        Index("ix_emo_journal_id", "journal_id"),
        Index("ix_emo_patient_username", "patient_username"),
        Index("ix_emo_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    journal_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=False)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)

    admiration = Column(Float, default=0.0)
    amusement = Column(Float, default=0.0)
    anger = Column(Float, default=0.0)
    annoyance = Column(Float, default=0.0)
    approval = Column(Float, default=0.0)
    caring = Column(Float, default=0.0)
    confusion = Column(Float, default=0.0)
    curiosity = Column(Float, default=0.0)
    desire = Column(Float, default=0.0)
    disappointment = Column(Float, default=0.0)
    disapproval = Column(Float, default=0.0)
    disgust = Column(Float, default=0.0)
    embarrassment = Column(Float, default=0.0)
    excitement = Column(Float, default=0.0)
    fear = Column(Float, default=0.0)
    gratitude = Column(Float, default=0.0)
    grief = Column(Float, default=0.0)
    joy = Column(Float, default=0.0)
    love = Column(Float, default=0.0)
    nervousness = Column(Float, default=0.0)
    optimism = Column(Float, default=0.0)
    pride = Column(Float, default=0.0)
    realization = Column(Float, default=0.0)
    relief = Column(Float, default=0.0)
    remorse = Column(Float, default=0.0)
    sadness = Column(Float, default=0.0)
    surprise = Column(Float, default=0.0)
    neutral = Column(Float, default=0.0)

    model_version = Column(String, default="1.0.0")
    created_at = Column(String, nullable=False)
