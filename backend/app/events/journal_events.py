from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JournalSubmitted:
    journal_id: int
    patient_username: str
    raw_content: str
    timestamp: str


@dataclass
class JournalSummarized:
    journal_id: int
    patient_username: str
    summary: str
    clinical_summary: str
    emotions: str
    ai_source: str
    risk_score: int = 0
    risk_triggered: bool = False


@dataclass
class JournalViewed:
    journal_id: int
    viewer_username: str
    patient_username: str
