from sqlalchemy import Column, Integer, String, Float, Text

from app.core.database import Base


class RingSensorLog(Base):
    __tablename__ = "ring_sensor_log"

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
