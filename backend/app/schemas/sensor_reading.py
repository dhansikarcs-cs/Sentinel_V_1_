from pydantic import BaseModel, Field


class SensorReadingCreate(BaseModel):
    heart_rate: int = Field(default=72, ge=30, le=250)
    rmssd: float = Field(default=0.0, ge=0, le=500)
    sdnn: float = Field(default=0.0, ge=0, le=500)
    temperature: float = Field(default=36.5, ge=34, le=42)
    device_id: str = ""


class SensorReadingResponse(BaseModel):
    id: int
    patient_username: str
    heart_rate: int
    rmssd: float
    sdnn: float
    temperature: float
    device_id: str
    logged_at: str

    class Config:
        from_attributes = True
