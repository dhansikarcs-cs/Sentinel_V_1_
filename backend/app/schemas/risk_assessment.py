from pydantic import BaseModel
from typing import Optional


class RiskAssessmentCreate(BaseModel):
    journal_id: Optional[int] = None
    emotion_result_id: Optional[int] = None
    sensor_reading_id: Optional[int] = None
    patient_username: str
    risk_score: int = 0
    triggered: bool = False
    confidence: float = 0.0
    explanation: str = ""


class RiskAssessmentResponse(BaseModel):
    id: int
    journal_id: Optional[int] = None
    emotion_result_id: Optional[int] = None
    sensor_reading_id: Optional[int] = None
    patient_username: str
    risk_score: int
    triggered: bool
    confidence: float
    explanation: str
    algorithm_version: str
    created_at: str

    class Config:
        from_attributes = True
