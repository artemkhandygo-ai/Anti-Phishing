from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.bot.telegram_api import request_json
from app.core.config import settings
from app.db.repositories import AppStateRepository
from app.services.incident_service import add_feedback

logger = logging.getLogger(__name__)
OFFSET_KEY = "telegram_feedback_offset"
VALID_FEEDBACK = {"safe", "confirmed_phishing", "false_positive"}


def _post(method: str, payload: dict[str, Any]) -> None:
    request_json(method, http_method="POST", payload=payload, raise_on_error=False)


def parse_feedback_callback(data: str | None) -> tuple[str, int] | None:
    parts = (data or "").split(":")
    if len(parts) != 3 or parts[0] != "feedback":
        return None
    feedback_type = parts[1].strip()
    if feedback_type not in VALID_FEEDBACK:
        return None
    try:
        incident_id = int(parts[2])
    except (TypeError, ValueError):
        return None
    return feedback_type, incident_id


def _ack_text(feedback_type: str) -> str:
    return {
        "safe": "Отмечено как безопасное",
        "confirmed_phishing": "Отмечено как фишинг",
        "false_positive": "Отмечено как ложное срабатывание",
    }.get(feedback_type, "Feedback saved")


def process_updates(db: Session) -> dict[str, int | str]:
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_FEEDBACK_POLL_ENABLED:
        return {"processed": 0, "saved": 0, "status": "disabled"}

    state_repo = AppStateRepository(db)
    offset_raw = state_repo.get(OFFSET_KEY, "0") or "0"
    try:
        offset = int(offset_raw)
    except ValueError:
        offset = 0

    payload = request_json(
        "getUpdates",
        params={"offset": offset, "timeout": 0, "allowed_updates": '["callback_query"]'},
        raise_on_error=False,
    )
    if not payload:
        logger.warning("Telegram getUpdates unavailable; keeping previous offset %s", offset)
        return {"processed": 0, "saved": 0, "status": "telegram_unavailable"}

    updates = payload.get("result", []) if payload.get("ok") else []

    processed = 0
    saved = 0
    next_offset = offset
    for update in updates:
        processed += 1
        next_offset = max(next_offset, int(update.get("update_id", 0)) + 1)
        callback = update.get("callback_query") or {}
        parsed = parse_feedback_callback(callback.get("data"))
        if not parsed:
            continue
        feedback_type, incident_id = parsed
        try:
            add_feedback(db, incident_id, feedback_type)
            saved += 1
            _post("answerCallbackQuery", {
                "callback_query_id": callback.get("id"),
                "text": _ack_text(feedback_type),
                "show_alert": False,
            })
            message = callback.get("message") or {}
            if message.get("message_id") is not None and message.get("chat", {}).get("id") is not None:
                _post("editMessageReplyMarkup", {
                    "chat_id": message["chat"]["id"],
                    "message_id": message["message_id"],
                    "reply_markup": {"inline_keyboard": []},
                })
        except Exception as exc:
            logger.warning("Failed to save feedback from Telegram callback: %s", exc)
            _post("answerCallbackQuery", {
                "callback_query_id": callback.get("id"),
                "text": "Не удалось сохранить feedback",
                "show_alert": False,
            })

    state_repo.set(OFFSET_KEY, str(next_offset))
    db.commit()
    return {"processed": processed, "saved": saved, "status": "ok"}
