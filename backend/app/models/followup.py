from sqlalchemy import Column, String, Text, ForeignKey

from app.core.database import Base
from app.core.encrypted_fields import EncryptedText


class FollowupTask(Base):
    __tablename__ = "followups"

    id = Column(String, primary_key=True)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    psychologist_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(EncryptedText, default="")
    file_path = Column(String, default="")
    status = Column(String, default="pending")
    grade = Column(String, default="")
    assigned_at = Column(String, default="")
    completed_at = Column(String, default="")
