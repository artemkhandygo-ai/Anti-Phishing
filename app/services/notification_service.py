from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.bot.message_builder import build_alert_message
from app.bot.telegram_bot import send_telegram_message
from app.core.config import settings
from app.db.models import TelegramNotification
from app.db.repositories import IncidentRepository, TelegramNotificationRepository

logger = logging.getLogger(__name__)


def queue_incident_notification(incident_id: int) -> None:
    if not settings.TELEGRAM_NOTIFICATION_ASYNC:
        return
    try:
        from app.tasks.notification_tasks import send_incident_notification_task

        send_incident_notification_task.delay(incident_id)
    except Exception as exc:
        logger.warning("Failed to enqueue incident notification %s: %s", incident_id, exc)


def send_incident_notification_now(db: Session, incident_id: int) -> dict:
    incident = IncidentRepository(db).get(incident_id)
    if incident is None or incident.email is None:
        return {"status": "not_found", "incident_id": incident_id}

    message = build_alert_message(incident, incident.email)
    result = send_telegram_message(message, incident_id=incident.id)

    TelegramNotificationRepository(db).create(
        incident_id=incident.id,
        chat_id=result.get("chat_id", "unknown"),
        telegram_message_id=result.get("message_id"),
        delivery_status=result.get("status", "failed"),
    )
    db.commit()
    return {
        "status": result.get("status", "failed"),
        "incident_id": incident_id,
        "message_id": result.get("message_id"),
        "chat_id": result.get("chat_id"),
    }
