from pydantic import BaseModel
from typing import Optional


class BookingCreate(BaseModel):
    psychologist_username: str
    date: str
    time: str
    session_type: str = ""
    members: str = ""
    contact: str = ""
    explanation: str = ""


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
    status: str


class AvailabilityCreate(BaseModel):
    date: str
    start_time: str = "09:00"
    end_time: str = "17:00"
