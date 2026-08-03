from sqlalchemy import Column, Integer, String, Float, ForeignKey

from app.core.database import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    device_id = Column(String, default="")

    heart_rate = Column(Integer, default=0)
    rmssd = Column(Float, default=0.0)
    sdnn = Column(Float, default=0.0)
    temperature = Column(Float, default=0.0)

    logged_at = Column(String, nullable=False)
