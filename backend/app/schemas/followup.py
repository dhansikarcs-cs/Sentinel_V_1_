from typing import Literal
from pydantic import BaseModel, Field


class FollowupCreate(BaseModel):
    patient_username: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)


class FollowupUpdate(BaseModel):
    status: Literal["pending", "completed", "skipped"] = "pending"
    grade: Literal["none", "red", "yellow", "green"] = "none"


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
