from sqlalchemy import Column, Integer, String, Text

from app.core.database import Base


class CrisisState(Base):
    __tablename__ = "crisis_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    active = Column(Integer, default=0)
    patient_username = Column(String, default="")
    triggered_at = Column(String, default="")
    triggered_by = Column(String, default="")
    acknowledged = Column(Integer, default=0)
    acknowledged_by = Column(String, default="")
    acknowledged_at = Column(String, default="")
    helpline_escalated = Column(Integer, default=0)
    trusted_contact_notified = Column(Integer, default=0)
    trustee_acknowledged = Column(Integer, default=0)
    trustee_clicked = Column(Integer, default=0)
    tc_ack_emailed = Column(Integer, default=0)
    helpline_ack_emailed = Column(Integer, default=0)


class CrisisLog(Base):
    __tablename__ = "crisis_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event = Column(String, nullable=False)
    patient = Column(String, default="")
    timestamp = Column(String, nullable=False)
    source = Column(String, default="")
    details = Column(Text, default="")
