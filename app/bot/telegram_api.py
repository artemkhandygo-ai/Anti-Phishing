from __future__ import annotations

import logging
import time
from typing import Any

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramApiError(Exception):
    pass


def api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"


def request_json(method: str, *, http_method: str = "GET", params: dict[str, Any] | None = None, payload: dict[str, Any] | None = None, raise_on_error: bool = False) -> dict[str, Any] | None:
    last_exc: Exception | None = None
    request_timeout = (5, settings.TELEGRAM_API_TIMEOUT_SECONDS)
    for attempt in range(settings.TELEGRAM_API_RETRIES + 1):
        try:
            if http_method.upper() == "POST":
                response = requests.post(api_url(method), json=payload, timeout=request_timeout)
            else:
                response = requests.get(api_url(method), params=params, timeout=request_timeout)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as exc:
            last_exc = exc
            logger.warning("Telegram API %s attempt %s failed: %s", method, attempt + 1, exc)
            if attempt < settings.TELEGRAM_API_RETRIES:
                time.sleep(settings.TELEGRAM_API_RETRY_SLEEP_SECONDS)
                continue
            break
    if raise_on_error and last_exc is not None:
        raise TelegramApiError(str(last_exc)) from last_exc
    return None
