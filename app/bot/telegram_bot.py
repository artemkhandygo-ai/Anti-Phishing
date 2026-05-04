import logging

from app.bot.keyboards import feedback_keyboard
from app.bot.telegram_api import request_json
from app.core.config import settings

logger = logging.getLogger(__name__)


def send_telegram_message(text: str, incident_id: int | None = None) -> dict:
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.warning("Telegram is not configured. Skipping notification.")
        return {"status": "skipped", "chat_id": "not_configured", "message_id": None}

    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": text,
        "reply_markup": feedback_keyboard(incident_id),
    }
    data = request_json("sendMessage", http_method="POST", payload=payload)
    if not data:
        return {"status": "failed", "chat_id": str(settings.TELEGRAM_CHAT_ID), "message_id": None}

    return {
        "status": "sent" if data.get("ok") else "failed",
        "chat_id": str(settings.TELEGRAM_CHAT_ID),
        "message_id": str(data.get("result", {}).get("message_id")),
    }
