from pydantic import BaseModel
from typing import Optional


class FollowupCreate(BaseModel):
    patient_username: str
    title: str
    description: str = ""


class FollowupUpdate(BaseModel):
    status: str = ""
    grade: str = ""


class FollowupResponse(BaseModel):
    id: str
    patient_username: str
    psychologist_username: str
    title: str
    description: str
    status: str
    grade: str
    assigned_at: str
    completed_at: str = ""

    class Config:
        from_attributes = True
