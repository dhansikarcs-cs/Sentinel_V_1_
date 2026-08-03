from pydantic import BaseModel


class TimelineEvent(BaseModel):
    type: str
    timestamp: str
    data: dict = {}


class ChangeMetrics(BaseModel):
    current_mood_avg: float | None = None
    previous_mood_avg: float | None = None
    mood_trend: str = "insufficient_data"
    mood_change_pct: float | None = None
    journal_count_7: int = 0
    journal_count_14: int = 0
    engagement_trend: str = "none"


class TimelineResponse(BaseModel):
    events: list[TimelineEvent]
    metrics: ChangeMetrics
