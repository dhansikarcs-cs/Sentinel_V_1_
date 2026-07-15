from sqlalchemy import Column, String, Integer, Text

from app.core.database import Base


class User(Base):
    __tablename__ = "patient_profiles"

    username = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="patient")
    age = Column(Integer, default=0)
    occupation = Column(String, default="")
    clinic_code = Column(String, default="")
    trusted_contact = Column(Text, default="")
    locked_until = Column(String, default="")
    failed_attempts = Column(Integer, default=0)
    assigned_psych = Column(String, default="")
    onboarding_step = Column(Integer, default=0)
    contact_info = Column(Text, default="")
    psych_trusted_contact = Column(Text, default="")
    encryption_salt = Column(String, default="")
    created_at = Column(String, nullable=False)
