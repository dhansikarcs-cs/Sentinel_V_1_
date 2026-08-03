from pydantic import BaseModel
from typing import Optional


class NotificationCreate(BaseModel):
    patient_username: str
    title: str
    message: str
    notification_type: str = "info"


class NotificationResponse(BaseModel):
    id: int
    patient_username: str
    title: str
    message: str
    notification_type: str
    read: bool
    sent_at: str

    class Config:
        from_attributes = True


class NotificationUpdate(BaseModel):
    read: bool = True
