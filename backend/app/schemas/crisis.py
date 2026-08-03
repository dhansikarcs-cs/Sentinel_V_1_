from pydantic import BaseModel


class CrisisStateResponse(BaseModel):
    active: bool
    patient: str = ""
    triggered_at: str = ""
    triggered_by: str = ""
    acknowledged: bool = False
    acknowledged_by: str = ""
    acknowledged_at: str = ""
    helpline_escalated: bool = False
    trusted_contact_notified: bool = False
    trustee_acknowledged: bool = False
    trustee_clicked: bool = False


class CrisisRiskResponse(BaseModel):
    risk_score: int
    reasoning: str
    triggered: bool
    contributing_factors: dict = {}


class CrisisLogResponse(BaseModel):
    id: int
    event: str
    patient: str
    timestamp: str
    source: str = ""
    details: str = ""

    class Config:
        from_attributes = True


class RiskAssessmentRequest(BaseModel):
    text: str
