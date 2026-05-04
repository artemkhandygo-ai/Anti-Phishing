import csv
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.base import Base
from app.db.models import Incident
from app.db.session import SessionLocal, engine

OUT = ROOT / "data" / "processed" / "feedback_dataset.csv"


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        incidents = db.scalars(
            select(Incident).options(selectinload(Incident.email), selectinload(Incident.reasons), selectinload(Incident.feedback))
        ).all()
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "incident_id", "email_id", "subject", "from_email", "risk_level", "status", "feedback", "reasons", "text_body"
            ])
            writer.writeheader()
            for incident in incidents:
                latest_feedback = incident.feedback[-1].feedback_type if incident.feedback else ""
                writer.writerow({
                    "incident_id": incident.id,
                    "email_id": incident.email_id,
                    "subject": incident.email.subject if incident.email else "",
                    "from_email": incident.email.from_email if incident.email else "",
                    "risk_level": incident.risk_level,
                    "status": incident.status,
                    "feedback": latest_feedback,
                    "reasons": ";".join(reason.reason_code for reason in incident.reasons),
                    "text_body": (incident.email.text_body if incident.email else "") or "",
                })
        print(OUT)
    finally:
        db.close()


if __name__ == "__main__":
    main()
