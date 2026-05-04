import csv
import io
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.repositories import IncidentRepository
from app.db.session import get_db
from app.schemas.feedback import FeedbackOut
from app.schemas.incident import FeedbackIn, IncidentOut
from app.services.incident_service import add_feedback

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _filtered_incidents(
    db: Session,
    limit: int = 1000,
    status: str | None = None,
    risk_level: str | None = None,
    days: int | None = None,
):
    incidents = IncidentRepository(db).list(limit=limit)
    if status:
        incidents = [item for item in incidents if item.status == status]
    if risk_level:
        incidents = [item for item in incidents if item.risk_level == risk_level]
    if days is not None:
        cutoff = datetime.utcnow() - timedelta(days=max(days, 0))
        incidents = [item for item in incidents if item.created_at >= cutoff]
    return incidents


@router.get(
    "",
    response_model=list[IncidentOut],
    summary="Список инцидентов",
    description="Возвращает последние инциденты антифишингового анализа.",
)
def list_incidents(limit: int = 50, db: Session = Depends(get_db)):
    return IncidentRepository(db).list(limit=limit)


@router.get(
    "/export.csv",
    summary="Экспорт инцидентов в CSV",
    description="Выгружает инциденты в CSV с фильтрами по статусу, уровню риска и дате.",
)
def export_incidents_csv(
    limit: int = Query(default=1000, le=50000),
    status: str | None = None,
    risk_level: str | None = None,
    days: int | None = None,
    db: Session = Depends(get_db),
):
    incidents = _filtered_incidents(db, limit=limit, status=status, risk_level=risk_level, days=days)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
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
        email_obj = incident.email
        writer.writerow([
            incident.id,
            incident.email_id,
            incident.created_at.isoformat(),
            incident.risk_level,
            incident.risk_score,
            incident.rule_score,
            incident.ml_score,
            incident.status,
            getattr(email_obj, "from_email", "") if email_obj else "",
            getattr(email_obj, "subject", "") if email_obj else "",
            ";".join(reason.reason_code for reason in incident.reasons),
            ";".join(item.feedback_type for item in incident.feedback),
        ])
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="incidents_export.csv"'},
    )


@router.get(
    "/export.json",
    summary="Экспорт инцидентов в JSON",
    description="Выгружает инциденты в JSON с фильтрами по статусу, уровню риска и дате.",
)
def export_incidents_json(
    limit: int = Query(default=1000, le=50000),
    status: str | None = None,
    risk_level: str | None = None,
    days: int | None = None,
    db: Session = Depends(get_db),
):
    incidents = _filtered_incidents(db, limit=limit, status=status, risk_level=risk_level, days=days)
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
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="incidents_export.json"'},
    )


@router.get("/{incident_id}", response_model=IncidentOut, include_in_schema=False)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = IncidentRepository(db).get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/{incident_id}/feedback", response_model=FeedbackOut, include_in_schema=False)
def create_feedback(incident_id: int, payload: FeedbackIn, db: Session = Depends(get_db)):
    try:
        return add_feedback(db, incident_id, payload.feedback_type)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
