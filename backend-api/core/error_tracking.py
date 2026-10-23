"""Sink local de erros — Sentry €0 (sempre activo). Sentry cloud se SENTRY_DSN."""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from paths import BACKEND_ROOT

logger = logging.getLogger("diomika-errors")
_lock = threading.Lock()
_ERROR_LOG = Path(os.getenv("ERROR_LOG_FILE") or (BACKEND_ROOT / "logs" / "errors.jsonl"))


def init_error_tracking() -> str:
    """Activa Sentry se houver DSN; senão ficheiro local. Devolve modo activo."""
    from core.sentry_init import init_sentry

    if init_sentry():
        return "sentry"
    _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Error tracking local activo: %s", _ERROR_LOG)
    return "local"


def capture_exception(exc: BaseException, *, path: str = "", request_id: str | None = None) -> None:
    try:
        import sentry_sdk

        if (os.getenv("SENTRY_DSN") or "").strip():
            sentry_sdk.capture_exception(exc)
            return
    except Exception:
        pass
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": type(exc).__name__,
        "msg": str(exc)[:500],
        "path": path,
        "request_id": request_id,
    }
    try:
        _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            with _ERROR_LOG.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        logger.debug("error sink write failed", exc_info=True)
