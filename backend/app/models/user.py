from sqlalchemy import Column, String, Integer, Text

from app.core.database import Base
from app.core.encrypted_fields import EncryptedText


class User(Base):
    __tablename__ = "patient_profiles"

    username = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="patient")
    age = Column(Integer, default=0)
    occupation = Column(String, default="")
    clinic_code = Column(String, default="")
    trusted_contact = Column(EncryptedText, default="")
    locked_until = Column(String, default="")
    failed_attempts = Column(Integer, default=0)
    assigned_psych = Column(String, default="")
    onboarding_step = Column(Integer, default=0)
    contact_info = Column(EncryptedText, default="")
    psych_trusted_contact = Column(EncryptedText, default="")
    consent_form = Column(String, default="")
    encryption_salt = Column(String, default="")
    created_at = Column(String, nullable=False)
    updated_at = Column(String, default="")
    deleted_at = Column(String, nullable=True, default=None)
    deleted_by = Column(String, nullable=True, default=None)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
