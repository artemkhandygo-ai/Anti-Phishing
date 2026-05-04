from __future__ import annotations

import logging
import time
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)


def run_migrations(retries: int = 10, sleep_seconds: float = 2.0) -> None:
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "app/db/migrations"))
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            command.upgrade(config, "head")
            logger.info("Database migrations applied")
            return
        except Exception as exc:  # pragma: no cover - startup dependent
            last_exc = exc
            logger.warning("Migration attempt %s/%s failed: %s", attempt + 1, retries, exc)
            time.sleep(sleep_seconds)
    if last_exc is not None:
        raise last_exc
