"""Deteção simples de abuso — transforma logs em alertas runtime."""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict

from core.alerts import send_alert

logger = logging.getLogger("diomika-anomaly")

_lock = threading.Lock()
_login_fails: dict[str, list[float]] = defaultdict(list)
_last_alert: dict[str, float] = {}


def note_login_failure(username: str, ip: str) -> None:
    """Se N falhas num janela → alerta crítico (throttled)."""
    threshold = int(os.getenv("ANOMALY_LOGIN_FAIL_THRESHOLD") or "8")
    window = int(os.getenv("ANOMALY_LOGIN_FAIL_WINDOW_SEC") or "600")
    cooldown = int(os.getenv("ANOMALY_ALERT_COOLDOWN_SEC") or "900")
    now = time.time()
    key = f"{(username or '').lower()}|{(ip or '')}"
    with _lock:
        hits = [t for t in _login_fails[key] if now - t < window]
        hits.append(now)
        _login_fails[key] = hits
        if len(hits) < threshold:
            return
        last = _last_alert.get(key, 0)
        if now - last < cooldown:
            return
        _last_alert[key] = now
    send_alert(
        "Anomalia: brute-force login admin",
        severity="critical",
        detail={"username": username, "ip": ip, "fails": len(hits), "window_sec": window},
    )
    logger.error("ANOMALY login fails user=%s ip=%s n=%s", username, ip, len(hits))
