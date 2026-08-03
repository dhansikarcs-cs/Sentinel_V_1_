from pydantic import BaseModel, Field


class SensorDataCreate(BaseModel):
    device_id: str = ""
    bpm: int = Field(default=72, ge=30, le=250)
    stress: int = Field(default=35, ge=0, le=100)
    sleep_hours: float = Field(default=7.0, ge=0, le=24)
    spo2: float = Field(default=98.0, ge=50, le=100)
    hrv: int = Field(default=50, ge=0, le=300)


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


class RingDeviceCreate(BaseModel):
    serial: str = Field(min_length=1, max_length=128)
    vendor: str = "simulated"


class RingDeviceResponse(BaseModel):
    serial: str
    patient_username: str
    vendor: str
    status: str
    last_seen_at: str
    created_at: str
    token: str = ""

    class Config:
        from_attributes = True
