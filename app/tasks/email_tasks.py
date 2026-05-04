from __future__ import annotations

import logging

from app.core.config import settings
from app.db.repositories import EmailRepository
from app.db.session import SessionLocal
from app.mail.mail_service import MailService
from app.services.analysis_service import analyze_message_object
from app.tasks.celery_app import celery_app
from app.tasks.locks import task_lock

logger = logging.getLogger(__name__)


def _load_messages(service: MailService, email_repo: EmailRepository, limit: int) -> tuple[list[dict], str]:
    existing_count = email_repo.count()
    if existing_count == 0:
        messages = service.fetch_initial_batch(limit=settings.MAIL_INITIAL_BOOTSTRAP_LIMIT)
        return messages, "initial_bootstrap"

    last_uid = email_repo.get_max_imap_uid()
    messages = service.fetch_new_since(last_uid=last_uid, limit=limit)
    return messages, "incremental"


@celery_app.task(name="app.tasks.email_tasks.fetch_and_analyze_emails")
def fetch_and_analyze_emails(limit: int | None = None) -> dict:
    db = SessionLocal()
    try:
        service = MailService()
        email_repo = EmailRepository(db)
        effective_limit = limit or settings.MAIL_FETCH_LIMIT
        messages, mode = _load_messages(service, email_repo, effective_limit)

        processed = 0
        skipped = 0
        errors = 0
        for item in messages:
            try:
                result = analyze_message_object(db, item["message"], item["imap_uid"])
                if result is None:
                    skipped += 1
                    continue
                processed += 1
            except Exception as exc:
                logger.exception("Failed to analyze IMAP message uid=%s: %s", item.get("imap_uid"), exc)
                db.rollback()
                errors += 1

        return {
            "mode": mode,
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
            "fetched": len(messages),
        }
    finally:
        db.close()


@celery_app.task(name="app.tasks.email_tasks.poll_mailbox")
def poll_mailbox() -> dict:
    with task_lock("lock:poll_mailbox", settings.MAIL_POLL_LOCK_TTL_SECONDS) as acquired:
        if not acquired:
            return {"status": "skipped_locked", "processed": 0, "skipped": 0, "errors": 0, "fetched": 0}
        return fetch_and_analyze_emails(limit=settings.MAIL_FETCH_LIMIT)
