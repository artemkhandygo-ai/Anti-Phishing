import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.base import Base
from app.db.repositories import IncidentRepository
from app.db.session import SessionLocal, engine


OUT_DIR = ROOT / "data" / "exports"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    incidents = IncidentRepository(db).list(limit=50000)

    csv_path = OUT_DIR / "incidents_export.csv"
    json_path = OUT_DIR / "incidents_export.json"

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "incident_id",
            "email_id",
            "created_at",
            "risk_level",
            "risk_score",
            "rule_score",
            "ml_score",
            "status",
            "from_email",
            "subject",
            "reason_codes",
            "feedback",
        ])
        for incident in incidents:
            writer.writerow([
                incident.id,
                incident.email_id,
                incident.created_at.isoformat(),
                incident.risk_level,
                incident.risk_score,
                incident.rule_score,
                incident.ml_score,
                incident.status,
                getattr(incident.email, "from_email", "") if incident.email else "",
                getattr(incident.email, "subject", "") if incident.email else "",
                ";".join(reason.reason_code for reason in incident.reasons),
                ";".join(item.feedback_type for item in incident.feedback),
            ])

    payload = []
    for incident in incidents:
        payload.append({
            "id": incident.id,
            "email_id": incident.email_id,
            "created_at": incident.created_at.isoformat(),
            "risk_level": incident.risk_level,
            "risk_score": incident.risk_score,
            "rule_score": incident.rule_score,
            "ml_score": incident.ml_score,
            "status": incident.status,
            "from_email": getattr(incident.email, "from_email", None) if incident.email else None,
            "subject": getattr(incident.email, "subject", None) if incident.email else None,
            "reasons": [
                {"reason_code": reason.reason_code, "reason_text": reason.reason_text, "severity": reason.severity}
                for reason in incident.reasons
            ],
            "feedback": [item.feedback_type for item in incident.feedback],
        })

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    db.close()
    print(csv_path)
    print(json_path)


if __name__ == "__main__":
    main()
