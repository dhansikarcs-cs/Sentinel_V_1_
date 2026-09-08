from pydantic import BaseModel, Field


class CheckInAnswer(BaseModel):
    question: str = Field(min_length=1, max_length=200)
    answer: str = Field(min_length=1, max_length=200)


class JournalCreate(BaseModel):
    raw_content: str = Field(min_length=1, max_length=10000)
    checkin: list[CheckInAnswer] = Field(default_factory=list)


class JournalResponse(BaseModel):
    id: int
    patient_username: str
    raw_content: str
    summary: str
    clinical_summary: str = ""
    ai_source: str
    emotions: str
    emotion_probabilities: str = ""
    timestamp: str

    class Config:
        from_attributes = True


class JournalSummary(BaseModel):
    id: int
    patient_username: str
    summary: str
    clinical_summary: str = ""
    ai_source: str
    emotions: str
    emotion_probabilities: str = ""
    timestamp: str

    class Config:
        from_attributes = True
