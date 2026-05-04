from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Incident
from app.db.repositories import FeedbackRepository, IncidentRepository


FEEDBACK_STATUS_MAP = {
    "safe": "feedback_safe",
    "false_positive": "feedback_false_positive",
    "confirmed_phishing": "feedback_confirmed_phishing",
}


def add_feedback(db: Session, incident_id: int, feedback_type: str):
    incident = IncidentRepository(db).get(incident_id)
    if incident is None:
        raise ValueError(f"Incident {incident_id} not found")

    latest = FeedbackRepository(db).latest_for_incident(incident_id)
    if latest and latest.feedback_type == feedback_type:
        return latest

    feedback = FeedbackRepository(db).create(incident_id=incident_id, feedback_type=feedback_type)
    incident.status = FEEDBACK_STATUS_MAP.get(feedback_type, incident.status)
    db.commit()
    db.refresh(feedback)
    return feedback
