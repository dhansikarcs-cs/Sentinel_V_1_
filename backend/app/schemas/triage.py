from pydantic import BaseModel


class TriageCreate(BaseModel):
    patient_username: str


class TriageUpdate(BaseModel):
    status: str = "open"
    priority: str = ""


class TriageResponse(BaseModel):
    id: str
    patient_username: str
    assessed_by: str
    priority: str
    urgency_score: int
    suggestion: str
    reasoning: str
    recent_mood: str
    bpm: int
    stress: int
    status: str
    created_at: str
    assessed_at: str

    class Config:
        from_attributes = True
