"""Rate limiting — in-memory (default) ou Redis se REDIS_URL estiver definido."""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict

from fastapi import HTTPException, Request
from starlette.responses import Response

from core.redis_client import get_redis, redis_available, reset_redis_client
from core.path_patterns import is_admin_or_system_path, is_public_catalog_path

logger = logging.getLogger("diomika-api")

_hits: dict[str, list[float]] = defaultdict(list)
_last_cleanup = 0.0

MAX_PUBLIC_BODY_LINES = 50
MAX_LINE_QUANTITY = 50_000

_EXEMPT_PATHS = frozenset({"/health", "/health/ready", "/api/docs", "/api/redoc", "/openapi.json"})


def trust_proxy_headers() -> bool:
    flag = (os.getenv("TRUST_PROXY") or "").strip().lower()
    return flag in ("1", "true", "yes")


def _trusted_proxy_entries() -> list[str]:
    raw = (os.getenv("TRUSTED_PROXY_IPS") or "127.0.0.1,::1").strip()
    return [ip.strip() for ip in raw.split(",") if ip.strip()]


def _ip_in_entry(ip: str, entry: str) -> bool:
    if "/" not in entry:
        return ip == entry
    try:
        import ipaddress

        return ipaddress.ip_address(ip) in ipaddress.ip_network(entry, strict=False)
    except Exception:
        return False


def _peer_is_trusted_proxy(request: Request) -> bool:
    if not request.client or not request.client.host:
        return False
    peer = request.client.host
    return any(_ip_in_entry(peer, entry) for entry in _trusted_proxy_entries())


def get_client_ip(request: Request) -> str:
    if trust_proxy_headers() and _peer_is_trusted_proxy(request):
        forwarded_for = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
        if forwarded_for:
            first_ip = forwarded_for.split(",")[0].strip()
            if first_ip:
                return first_ip
        real_ip = request.headers.get("x-real-ip") or request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
    client = getattr(request, "client", None)
    return client.host if client else "unknown"


def _limits_for_path(method: str, path: str) -> tuple[str, int]:
    if is_admin_or_system_path(path):
        return "admin", int(os.getenv("RATE_LIMIT_ADMIN_PER_MIN", "300"))
    if method == "GET" and is_public_catalog_path(path):
        return "catalog", int(os.getenv("RATE_LIMIT_CATALOG_PER_MIN", "600"))
    return "global", int(os.getenv("RATE_LIMIT_GLOBAL_PER_MIN", "120"))


def _is_loopback_ip(ip: str) -> bool:
    peer = (ip or "").strip().lower()
    return peer in {"127.0.0.1", "::1", "localhost", "testclient"} or peer.startswith("127.")


def _window_seconds() -> int:
    return max(10, int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")))


def _maybe_cleanup(now: float) -> None:
    global _last_cleanup
    if now - _last_cleanup < 120:
        return
    _last_cleanup = now
    cutoff = now - _window_seconds() * 2
    stale = [k for k, hits in _hits.items() if not hits or hits[-1] < cutoff]
    for k in stale:
        del _hits[k]


def _record_and_check_memory(key: str, max_calls: int, window_seconds: int) -> bool:
    now = time.time()
    cutoff = now - window_seconds
    hits = _hits[key]
    _hits[key] = [t for t in hits if t > cutoff]
    if len(_hits[key]) >= max_calls:
        return False
    _hits[key].append(now)
    _maybe_cleanup(now)
    return True


def _record_and_check_redis(key: str, max_calls: int, window_seconds: int) -> bool | None:
    client = get_redis()
    if client is None:
        return None
    rkey = f"diomika:rl:{key}"
    try:
        pipe = client.pipeline()
        now = time.time()
        pipe.zremrangebyscore(rkey, 0, now - window_seconds)
        pipe.zcard(rkey)
        pipe.zadd(rkey, {f"{now}:{os.getpid()}": now})
        pipe.expire(rkey, window_seconds + 5)
        _, count, _, _ = pipe.execute()
        return int(count) < max_calls
    except Exception as exc:
        logger.debug("Redis rate limit falhou: %s", exc)
        return None


def _record_and_check(key: str, max_calls: int, window_seconds: int) -> bool:
    redis_result = _record_and_check_redis(key, max_calls, window_seconds)
    if redis_result is not None:
        return redis_result
    return _record_and_check_memory(key, max_calls, window_seconds)


def check_global_rate_limit(request: Request) -> Response | None:
    path = request.url.path
    if path in _EXEMPT_PATHS:
        return None

    client = get_client_ip(request)
    if (path.startswith("/admin") or path.startswith("/system")) and _is_loopback_ip(client):
        return None

    bucket, max_calls = _limits_for_path(request.method, path)
    key = f"{bucket}:{client}"
    if _record_and_check(key, max_calls, _window_seconds()):
        return None
    return Response("Demasiados pedidos", status_code=429)


def rate_limit(request: Request, key_prefix: str, max_calls: int = 5, window_seconds: int = 60):
    client = get_client_ip(request)
    key = f"{key_prefix}:{client}"
    if not _record_and_check(key, max_calls, window_seconds):
        raise HTTPException(
            status_code=429,
            detail="Demasiados pedidos. Tente novamente dentro de um minuto.",
        )


def rate_limit_absolute(key: str, max_calls: int = 5, window_seconds: int = 60):
    if not _record_and_check(key, max_calls, window_seconds):
        raise HTTPException(
            status_code=429,
            detail="Demasiados pedidos. Tente novamente dentro de um minuto.",
        )
