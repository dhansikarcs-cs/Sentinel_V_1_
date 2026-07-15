from sqlalchemy import Column, Integer, String, Text, ForeignKey

from app.core.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    psychologist_username = Column(String, default="")
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    session_type = Column(String, default="")
    members = Column(String, default="")
    contact = Column(String, default="")
    explanation = Column(String, default="")
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
