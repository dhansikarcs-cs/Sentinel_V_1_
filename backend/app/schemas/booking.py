from typing import Literal

from pydantic import BaseModel, Field


class BookingCreate(BaseModel):
    psychologist_username: str = Field(min_length=1, max_length=50)
    date: str = Field(min_length=10, max_length=10)
    time: str = Field(min_length=1, max_length=10)
    session_type: str = Field(default="", max_length=50)
    members: str = Field(default="", max_length=200)
    contact: str = Field(default="", max_length=200)
    explanation: str = Field(default="", max_length=2000)


class BookingResponse(BaseModel):
    id: int
    patient_username: str
    psychologist_username: str
    date: str
    time: str
    session_type: str
    status: str
    created_at: str

    class Config:
        from_attributes = True


class BookingUpdate(BaseModel):
    status: Literal["Pending", "Approved", "Rejected", "Cancelled"]


class AvailabilityCreate(BaseModel):
    date: str
    start_time: str = "09:00"
    end_time: str = "17:00"
