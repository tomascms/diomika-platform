"""Health check expandido."""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone

from paths import BACKEND_ROOT
from core.config import get_settings
from core.database import get_db
from core.resilience import get_smtp_breaker
from core.version import VERSION

_outbox_cache: dict = {"value": -1, "at": 0.0}
_OUTBOX_CACHE_SEC = 30
_DB_TIMEOUT_SEC = 2


def _worker_status() -> dict:
    state_file = BACKEND_ROOT / "data" / ".email_worker_state.json"
    worker_file = BACKEND_ROOT / ".email_worker_heartbeat.json"
    status = {"running": False, "last_poll": None}
    if worker_file.exists():
        try:
            data = json.loads(worker_file.read_text(encoding="utf-8"))
            last = data.get("last_poll")
            status["last_poll"] = last
            if last:
                last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - last_dt).total_seconds()
                status["running"] = age < 120
        except Exception:
            pass
    status["state_file"] = state_file.exists()
    return status


def _outbox_pending() -> int:
    res = get_db().table("outbox_events").select("id", count="exact").eq("status", "pending").execute()
    return res.count or 0


def _outbox_pending_cached() -> int:
    now = time.time()
    if now - _outbox_cache["at"] < _OUTBOX_CACHE_SEC:
        return _outbox_cache["value"]
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_outbox_pending)
            value = fut.result(timeout=_DB_TIMEOUT_SEC)
    except (FuturesTimeout, Exception):
        value = _outbox_cache["value"]
    _outbox_cache["value"] = value
    _outbox_cache["at"] = now
    return value


def _pg_ping() -> bool:
    """Fallback quando o REST Supabase falha (ex.: CA partida no host) mas o Postgres responde."""
    try:
        from core.database_url import iter_database_urls
        import psycopg2

        for raw in iter_database_urls():
            url = raw
            if "sslmode=" not in url:
                url += ("&" if "?" in url else "?") + "sslmode=require"
            try:
                conn = psycopg2.connect(url, connect_timeout=5)
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        cur.fetchone()
                finally:
                    conn.close()
                return True
            except Exception:
                continue
        return False
    except Exception:
        return False


def _db_ping() -> bool:
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(lambda: get_db().table("outbox_events").select("id").limit(1).execute())
            fut.result(timeout=_DB_TIMEOUT_SEC)
        return True
    except (FuturesTimeout, Exception):
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(_pg_ping)
                return bool(fut.result(timeout=8))
        except (FuturesTimeout, Exception):
            return False


def build_health(*, detailed: bool = False, ready: bool = False) -> dict:
    if ready:
        ok = _db_ping()
        return {"status": "ready" if ok else "degraded", "database": ok}
    if not detailed:
        return {"status": "online", "version": VERSION}

    from core.notify import contact_notify_email
    from core.cache import cache_backend, cache_stats
    from core.rate_limit import redis_available
    from core.feature_flags import flags_snapshot
    from utils.storage import storage_is_private
    import os

    settings = get_settings()
    breaker = get_smtp_breaker()
    db_ok = _db_ping()
    worker = _worker_status()
    pending = _outbox_pending_cached()
    return {
        "status": "online",
        "version": VERSION,
        "env": settings.env,
        "database": db_ok,
        "storage": "private" if storage_is_private() else "public",
        "rate_limit": "redis" if redis_available() else "memory",
        "catalog_cache": cache_backend(),
        "catalog_cache_stats": cache_stats(),
        "api_key_required": settings.api_key_required,
        "contact_email_notify": bool(contact_notify_email()),
        "smtp_circuit": "open" if breaker.opened_at else "closed",
        "email_worker": worker,
        "outbox_pending": pending,
        "feature_flags": flags_snapshot(),
        "sentry": bool((os.getenv("SENTRY_DSN") or "").strip()),
        "axiom": bool((os.getenv("AXIOM_TOKEN") or "").strip()),
    }
