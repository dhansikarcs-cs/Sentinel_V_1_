from pydantic import BaseModel


class RiskAssessmentCreate(BaseModel):
    journal_id: int | None = None
    emotion_result_id: int | None = None
    sensor_reading_id: int | None = None
    patient_username: str
    risk_score: int = 0
    triggered: bool = False
    confidence: float = 0.0
    explanation: str = ""


class RiskAssessmentResponse(BaseModel):
    id: int
    journal_id: int | None = None
    emotion_result_id: int | None = None
    sensor_reading_id: int | None = None
    patient_username: str
    risk_score: int
    triggered: bool
    confidence: float
    explanation: str
    algorithm_version: str
    created_at: str

    class Config:
        from_attributes = True
