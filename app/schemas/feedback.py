from datetime import datetime
from pydantic import BaseModel


class FeedbackOut(BaseModel):
    id: int
    incident_id: int
    feedback_type: str
    created_at: datetime

    class Config:
        from_attributes = True
