from pydantic import BaseModel


class EmotionResultCreate(BaseModel):
    journal_id: int
    patient_username: str
    admiration: float = 0.0
    amusement: float = 0.0
    anger: float = 0.0
    annoyance: float = 0.0
    approval: float = 0.0
    caring: float = 0.0
    confusion: float = 0.0
    curiosity: float = 0.0
    desire: float = 0.0
    disappointment: float = 0.0
    disapproval: float = 0.0
    disgust: float = 0.0
    embarrassment: float = 0.0
    excitement: float = 0.0
    fear: float = 0.0
    gratitude: float = 0.0
    grief: float = 0.0
    joy: float = 0.0
    love: float = 0.0
    nervousness: float = 0.0
    optimism: float = 0.0
    pride: float = 0.0
    realization: float = 0.0
    relief: float = 0.0
    remorse: float = 0.0
    sadness: float = 0.0
    surprise: float = 0.0
    neutral: float = 0.0


class EmotionResultResponse(BaseModel):
    id: int
    journal_id: int
    patient_username: str
    admiration: float
    amusement: float
    anger: float
    annoyance: float
    approval: float
    caring: float
    confusion: float
    curiosity: float
    desire: float
    disappointment: float
    disapproval: float
    disgust: float
    embarrassment: float
    excitement: float
    fear: float
    gratitude: float
    grief: float
    joy: float
    love: float
    nervousness: float
    optimism: float
    pride: float
    realization: float
    relief: float
    remorse: float
    sadness: float
    surprise: float
    neutral: float
    model_version: str
    created_at: str

    class Config:
        from_attributes = True
