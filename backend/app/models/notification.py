from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notif_patient_username", "patient_username"),
        Index("ix_notif_read", "read"),
        Index("ix_notif_type", "notification_type"),
        Index("ix_notif_sent_at", "sent_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    title = Column(String, default="")
    message = Column(Text, default="")
    notification_type = Column(String, default="info")  # info | alert | crisis | reminder
    read = Column(Integer, default=0)
    sent_at = Column(String, nullable=False)
