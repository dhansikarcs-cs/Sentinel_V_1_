from pydantic import BaseModel
from typing import Optional


class AIAnalysisCreate(BaseModel):
    journal_id: int
    patient_username: str
    summary_patient: str = ""
    summary_clinical: str = ""
    priority: str = "low"
    confidence: float = 0.0
    explanation: str = ""
    provider: str = "rule"


class AIAnalysisResponse(BaseModel):
    id: int
    journal_id: int
    patient_username: str
    summary_patient: str
    summary_clinical: str
    priority: str
    confidence: float
    explanation: str
    provider: str
    model_version: str
    created_at: str

    class Config:
        from_attributes = True
