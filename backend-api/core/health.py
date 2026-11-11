"""Health check expandido."""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone

from paths import BACKEND_ROOT, heartbeat_path
from core.config import get_settings
from core.database import get_db
from core.resilience import get_smtp_breaker
from core.version import GIT_SHA, VERSION

_outbox_cache: dict = {"value": -1, "at": 0.0}
_OUTBOX_CACHE_SEC = 30
_DB_TIMEOUT_SEC = 2
_READY_CACHE_SEC = 10
_EMAIL_STALE_SEC = 15 * 60
# Pool global e sem `with`: o `with` esperava pela tarefa ao sair e o limite deixava de o ser (API-15).
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="health")
_ready_cache: dict = {"body": None, "at": 0.0}
_ready_lock = threading.Lock()


def _worker_status() -> dict:
    state_file = BACKEND_ROOT / "data" / ".email_worker_state.json"
    worker_file = heartbeat_path(BACKEND_ROOT)
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
        value = _pool.submit(_outbox_pending).result(timeout=_DB_TIMEOUT_SEC)
    except (FuturesTimeout, Exception):
        value = _outbox_cache["value"]
    _outbox_cache["value"] = value
    _outbox_cache["at"] = now
    return value


def _db_ping() -> bool:
    """Ping à BD com limite real: o fio fica a correr se passar de _DB_TIMEOUT_SEC, mas quem pede não espera."""
    try:
        _pool.submit(lambda: get_db().table("outbox_events").select("id").limit(1).execute()).result(
            timeout=_DB_TIMEOUT_SEC
        )
        return True
    except (FuturesTimeout, Exception):
        return False


def _ready_cached() -> dict:
    """Resultado de /health/ready durante _READY_CACHE_SEC: sondas e curiosos não geram uma consulta cada."""
    now = time.monotonic()
    with _ready_lock:
        if now - _ready_cache["at"] < _READY_CACHE_SEC and _ready_cache["body"] is not None:
            return _ready_cache["body"]
    ok = _db_ping()
    stale = _email_worker_stale()
    body = {
        "status": "ready" if ok and not stale else "degraded",
        "database": ok,
        "email_worker_stale": stale,
    }
    with _ready_lock:
        _ready_cache.update(body=body, at=time.monotonic())
    return body


def _email_worker_stale() -> bool:
    last = _worker_status()["last_poll"]
    if not last:
        return False  # sem heartbeat ainda (arranque): não se sabe, não se acusa
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(last.replace("Z", "+00:00"))).total_seconds()
    except ValueError:
        return False
    return age > _EMAIL_STALE_SEC


def build_health(*, detailed: bool = False, ready: bool = False) -> dict:
    if ready:
        return _ready_cached()
    if not detailed:
        return {"status": "online"}  # sem versão: não ajuda quem procura CVEs (SEG-20); o commit está em /health/detail

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
        "git_sha": GIT_SHA,
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
