from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import AppState, Email, Incident, IncidentFeedback, IncidentReason, TelegramNotification


class EmailRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Email:
        email = Email(**kwargs)
        self.db.add(email)
        self.db.flush()
        return email

    def get(self, email_id: int) -> Email | None:
        return self.db.get(Email, email_id)

    def get_by_imap_uid(self, imap_uid: str | None) -> Email | None:
        if not imap_uid:
            return None
        stmt = select(Email).where(Email.imap_uid == imap_uid).limit(1)
        return self.db.scalar(stmt)

    def get_by_message_id(self, message_id: str | None) -> Email | None:
        if not message_id:
            return None
        stmt = select(Email).where(Email.message_id == message_id).limit(1)
        return self.db.scalar(stmt)

    def count(self) -> int:
        return int(self.db.scalar(select(func.count(Email.id))) or 0)

    def get_max_imap_uid(self) -> int | None:
        rows = self.db.scalars(select(Email.imap_uid).where(Email.imap_uid.is_not(None))).all()
        numeric = []
        for value in rows:
            try:
                numeric.append(int(value))
            except (TypeError, ValueError):
                continue
        return max(numeric) if numeric else None

    def list(self, limit: int = 50) -> list[Email]:
        stmt = select(Email).order_by(Email.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())


class IncidentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Incident:
        incident = Incident(**kwargs)
        self.db.add(incident)
        self.db.flush()
        return incident

    def get(self, incident_id: int) -> Incident | None:
        stmt = (
            select(Incident)
            .where(Incident.id == incident_id)
            .options(selectinload(Incident.reasons), selectinload(Incident.feedback), selectinload(Incident.email))
            .limit(1)
        )
        return self.db.scalar(stmt)

    def list(self, limit: int = 50) -> list[Incident]:
        stmt = (
            select(Incident)
            .options(selectinload(Incident.reasons), selectinload(Incident.feedback), selectinload(Incident.email))
            .order_by(Incident.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def summary(self) -> dict:
        total = self.db.scalar(select(func.count(Incident.id))) or 0
        safe = self.db.scalar(select(func.count(Incident.id)).where(Incident.risk_level == "safe")) or 0
        suspicious = self.db.scalar(select(func.count(Incident.id)).where(Incident.risk_level == "suspicious")) or 0
        phishing = self.db.scalar(select(func.count(Incident.id)).where(Incident.risk_level == "phishing")) or 0
        return {
            "total_incidents": total,
            "safe": safe,
            "suspicious": suspicious,
            "phishing": phishing,
        }


class FeedbackRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, incident_id: int, feedback_type: str) -> IncidentFeedback:
        feedback = IncidentFeedback(incident_id=incident_id, feedback_type=feedback_type)
        self.db.add(feedback)
        self.db.flush()
        return feedback

    def latest_for_incident(self, incident_id: int) -> IncidentFeedback | None:
        stmt = (
            select(IncidentFeedback)
            .where(IncidentFeedback.incident_id == incident_id)
            .order_by(IncidentFeedback.created_at.desc(), IncidentFeedback.id.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def feedback_summary_by_reason(self) -> dict[str, dict[str, int]]:
        rows = (
            self.db.query(IncidentReason.reason_code, IncidentFeedback.feedback_type, func.count(IncidentFeedback.id))
            .join(Incident, Incident.id == IncidentReason.incident_id)
            .join(IncidentFeedback, IncidentFeedback.incident_id == Incident.id)
            .group_by(IncidentReason.reason_code, IncidentFeedback.feedback_type)
            .all()
        )
        out: dict[str, dict[str, int]] = {}
        for reason_code, feedback_type, count in rows:
            out.setdefault(reason_code, {})[feedback_type] = int(count)
        return out


class TelegramNotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> TelegramNotification:
        notification = TelegramNotification(**kwargs)
        self.db.add(notification)
        self.db.flush()
        return notification

    def get_by_message(self, chat_id: str, telegram_message_id: str | None) -> TelegramNotification | None:
        if not telegram_message_id:
            return None
        stmt = (
            select(TelegramNotification)
            .where(TelegramNotification.chat_id == str(chat_id), TelegramNotification.telegram_message_id == str(telegram_message_id))
            .limit(1)
        )
        return self.db.scalar(stmt)


class AppStateRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str, default: str | None = None) -> str | None:
        obj = self.db.get(AppState, key)
        return obj.value if obj else default

    def set(self, key: str, value: str | None) -> AppState:
        obj = self.db.get(AppState, key)
        if obj is None:
            obj = AppState(key=key, value=value)
            self.db.add(obj)
        else:
            obj.value = value
        self.db.flush()
        return obj
