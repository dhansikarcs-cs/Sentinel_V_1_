from pydantic import BaseModel
from typing import Optional


class SensorDataCreate(BaseModel):
    device_id: str = ""
    bpm: int = 72
    stress: int = 35
    sleep_hours: float = 7.0
    spo2: float = 98.0
    hrv: int = 50


class SensorDataResponse(BaseModel):
    id: int
    device_id: str
    patient_username: str
    bpm: int
    stress: int
    sleep_hours: float
    spo2: float
    hrv: int
    logged_at: str

    class Config:
        from_attributes = True
