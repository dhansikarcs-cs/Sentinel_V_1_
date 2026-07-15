from pydantic import BaseModel, Field
from typing import Optional


class JournalCreate(BaseModel):
    raw_content: str = Field(min_length=1, max_length=10000)


class JournalResponse(BaseModel):
    id: int
    patient_username: str
    raw_content: str
    summary: str
    ai_source: str
    emotions: str
    timestamp: str

    class Config:
        from_attributes = True


class JournalSummary(BaseModel):
    id: int
    patient_username: str
    summary: str
    ai_source: str
    emotions: str
    timestamp: str

    class Config:
        from_attributes = True
