from datetime import timedelta

from celery import Celery

from app.core.config import settings
from app.db.migrate import run_migrations

celery_app = Celery(
    "phishguard",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.training_tasks",
    ],
)

beat_schedule = {}
if settings.MAIL_POLL_ENABLED:
    beat_schedule["poll-mailbox-every-60-seconds"] = {
        "task": "app.tasks.email_tasks.poll_mailbox",
        "schedule": timedelta(seconds=settings.MAIL_POLL_INTERVAL_SECONDS),
        "options": {"queue": "emails"},
    }

if settings.TELEGRAM_FEEDBACK_POLL_ENABLED:
    beat_schedule["poll-telegram-feedback"] = {
        "task": "app.tasks.notification_tasks.poll_telegram_feedback",
        "schedule": timedelta(seconds=settings.TELEGRAM_FEEDBACK_POLL_INTERVAL_SECONDS),
        "options": {"queue": "notifications"},
    }

celery_app.conf.update(
    task_default_queue="celery",
    task_create_missing_queues=True,
    broker_connection_retry_on_startup=True,
    beat_schedule=beat_schedule,
    timezone="UTC",
    task_track_started=True,
    task_routes={
        "app.tasks.email_tasks.fetch_and_analyze_emails": {"queue": "emails"},
        "app.tasks.email_tasks.poll_mailbox": {"queue": "emails"},
        "app.tasks.notification_tasks.send_test_notification": {"queue": "notifications"},
        "app.tasks.notification_tasks.send_incident_notification": {"queue": "notifications"},
        "app.tasks.notification_tasks.poll_telegram_feedback": {"queue": "notifications"},
        "app.tasks.training_tasks.train_model_task": {"queue": "trainer"},
    },
)


if settings.AUTO_MIGRATE:
    run_migrations()
