from sqlalchemy.orm import Session

from app.db.repositories import IncidentRepository


def get_summary(db: Session) -> dict:
    return IncidentRepository(db).summary()
