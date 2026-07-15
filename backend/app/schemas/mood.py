from pydantic import BaseModel
from typing import Optional


class MoodCreate(BaseModel):
    date: str
    emoji: str
    label: str


class MoodResponse(BaseModel):
    id: int
    patient_username: str
    date: str
    emoji: str
    label: str
    timestamp: str

    class Config:
        from_attributes = True
