from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.core.config import settings


@lru_cache(maxsize=1)
def load_whitelist_entries() -> set[str]:
    path = Path(settings.WHITELIST_PATH)
    if not path.exists():
        return set()
    entries: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip().lower()
        if not value or value.startswith("#"):
            continue
        entries.add(value)
    return entries


def is_whitelisted_email(from_email: str | None) -> bool:
    if not from_email:
        return False
    sender = from_email.strip().lower()
    entries = load_whitelist_entries()
    if sender in entries:
        return True
    if "@" in sender:
        domain = sender.split("@", 1)[1]
        if f"@{domain}" in entries:
            return True
    return False


def refresh_whitelist_cache() -> None:
    load_whitelist_entries.cache_clear()
