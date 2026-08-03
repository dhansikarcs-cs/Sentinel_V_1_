from pydantic import BaseModel, Field

VALID_MOOD_LABELS = {"great", "good", "okay", "bad", "awful", "terrible"}


class MoodCreate(BaseModel):
    date: str = Field(min_length=10, max_length=10)
    emoji: str = Field(min_length=1, max_length=10)
    label: str = Field(min_length=1, max_length=20)


class MoodResponse(BaseModel):
    id: int
    patient_username: str
    date: str
    emoji: str
    label: str
    timestamp: str

    class Config:
        from_attributes = True
