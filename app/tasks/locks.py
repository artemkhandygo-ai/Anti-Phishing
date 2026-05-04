from __future__ import annotations

import logging
from contextlib import contextmanager
from functools import lru_cache

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


@contextmanager
def task_lock(lock_name: str, ttl_seconds: int):
    token = lock_name
    client = get_redis_client()
    acquired = False
    try:
        acquired = bool(client.set(lock_name, token, nx=True, ex=max(ttl_seconds, 1)))
    except RedisError as exc:
        logger.warning("Failed to acquire redis lock %s: %s", lock_name, exc)
        acquired = True
    try:
        yield acquired
    finally:
        if acquired:
            try:
                current = client.get(lock_name)
                if current == token:
                    client.delete(lock_name)
            except RedisError as exc:
                logger.warning("Failed to release redis lock %s: %s", lock_name, exc)
