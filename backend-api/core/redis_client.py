"""Cliente Redis partilhado — cache, rate-limit, sessões admin."""
from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger("diomika-api")

_redis = None
_redis_next_try = 0.0
_REDIS_RETRY_SEC = 20.0


def get_redis():
    global _redis, _redis_next_try
    if _redis is not None:
        return _redis
    now = time.time()
    if now < _redis_next_try:
        return None
    url = (os.getenv("REDIS_URL") or "").strip()
    if not url:
        _redis_next_try = now + _REDIS_RETRY_SEC
        return None
    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1.5)
        client.ping()
        _redis = client
        _redis_next_try = 0.0
        logger.info("Redis activo")
    except Exception as exc:
        logger.warning(
            "Redis indisponível (%s) — fallback in-memory; retry em %.0fs",
            exc,
            _REDIS_RETRY_SEC,
        )
        _redis = None
        _redis_next_try = now + _REDIS_RETRY_SEC
    return _redis


def redis_available() -> bool:
    return get_redis() is not None


def reset_redis_client() -> None:
    global _redis, _redis_next_try
    _redis = None
    _redis_next_try = 0.0
