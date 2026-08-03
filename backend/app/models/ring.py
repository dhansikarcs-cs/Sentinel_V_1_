from sqlalchemy import Column, Float, Index, Integer, String, Text

from app.core.database import Base


class RingSensorLog(Base):
    __tablename__ = "ring_sensor_log"
    __table_args__ = (
        Index("ix_ring_patient_username", "patient_username"),
        Index("ix_ring_logged_at", "logged_at"),
        Index("ix_ring_device_id", "device_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, default="")
    patient_username = Column(String, default="")
    bpm = Column(Integer, default=0)
    stress = Column(Integer, default=0)
    sleep_hours = Column(Float, default=0)
    spo2 = Column(Float, default=0)
    hrv = Column(Integer, default=0)
    raw_json = Column(Text, default="")  # FIXME: normalize into structured columns when ring firmware v2 ships
    logged_at = Column(String, nullable=False)
