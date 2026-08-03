from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index, CheckConstraint

from app.core.database import Base
from app.core.encrypted_fields import EncryptedText


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_booking_patient_username", "patient_username"),
        Index("ix_booking_psychologist_username", "psychologist_username"),
        Index("ix_booking_status", "status"),
        Index("ix_booking_date", "date"),
        CheckConstraint("status IN ('Pending', 'Approved', 'Rejected', 'Cancelled', 'Proposed', 'Completed')", name="ck_booking_status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    psychologist_username = Column(String, default="")
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    session_type = Column(String, default="")
    members = Column(String, default="")
    contact = Column(EncryptedText, default="")
    explanation = Column(EncryptedText, default="")
    status = Column(String, default="Pending")
    created_at = Column(String, nullable=False)


class PsychAvailability(Base):
    __tablename__ = "psych_availability"

    id = Column(Integer, primary_key=True, autoincrement=True)
    psychologist_username = Column(String, nullable=False)
    date = Column(String, nullable=False)
    start_time = Column(String, default="09:00")
    end_time = Column(String, default="17:00")
    created_at = Column(String, nullable=False)
