from __future__ import annotations

from app.bot.telegram_bot import send_telegram_message
from app.db.session import SessionLocal
from app.services.notification_service import send_incident_notification_now
from app.services.telegram_feedback_service import process_updates
from app.tasks.celery_app import celery_app
from app.tasks.locks import task_lock
from app.core.config import settings


@celery_app.task(name="app.tasks.notification_tasks.send_test_notification")
def send_test_notification(text: str = "PhishGuard test notification") -> dict:
    return send_telegram_message(text)


@celery_app.task(name="app.tasks.notification_tasks.send_incident_notification")
def send_incident_notification_task(incident_id: int) -> dict:
    db = SessionLocal()
    try:
        with task_lock(f"lock:incident_notify:{incident_id}", settings.NOTIFICATION_TASK_LOCK_TTL_SECONDS) as acquired:
            if not acquired:
                return {"status": "skipped_locked", "incident_id": incident_id}
            return send_incident_notification_now(db, incident_id)
    finally:
        db.close()


@celery_app.task(name="app.tasks.notification_tasks.poll_telegram_feedback")
def poll_telegram_feedback() -> dict:
    db = SessionLocal()
    try:
        with task_lock("lock:poll_telegram_feedback", settings.TELEGRAM_POLL_LOCK_TTL_SECONDS) as acquired:
            if not acquired:
                return {"processed": 0, "saved": 0, "status": "skipped_locked"}
            return process_updates(db)
    finally:
        db.close()
