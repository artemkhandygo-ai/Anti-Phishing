from datetime import datetime
from pydantic import BaseModel

from app.schemas.feedback import FeedbackOut


class IncidentReasonOut(BaseModel):
    reason_code: str
    reason_text: str
    severity: str

    class Config:
        from_attributes = True


class IncidentOut(BaseModel):
    id: int
    email_id: int
    risk_level: str
    risk_score: float
    rule_score: float
    ml_score: float
    model_version: str | None = None
    status: str
    created_at: datetime
    reasons: list[IncidentReasonOut] = []
    feedback: list[FeedbackOut] = []

    class Config:
        from_attributes = True


class FeedbackIn(BaseModel):
    feedback_type: str
