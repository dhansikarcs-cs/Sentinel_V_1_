from pydantic import BaseModel


class PsychJournalCreate(BaseModel):
    raw_content: str


class PsychJournalResponse(BaseModel):
    id: int
    summary: str
    ai_source: str = ""
    emotions: str = ""
    timestamp: str

    class Config:
        from_attributes = True
