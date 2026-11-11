"""Alertas operacionais — webhook validado (SSRF) + ficheiro local."""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.request
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import PROJECT_ROOT

logger = logging.getLogger("diomika-alerts")

_ALERT_LOG = Path(os.getenv("ALERT_LOG_FILE") or (PROJECT_ROOT / "deploy" / "alerts.log"))


# Um só fio para o webhook: send_alert nunca espera pela rede (corria dentro do event loop, SEG-17/API-04).
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="alerts")
_DEDUPE_SECONDS = 600
_last_sent: dict[str, float] = {}
_dedupe_lock = threading.Lock()


def _duplicate(title: str, window: float) -> bool:
    """True se o mesmo título já saiu há menos de `window` s; senão regista agora."""
    if window <= 0:
        return False
    now = time.monotonic()
    with _dedupe_lock:
        if now - _last_sent.get(title, -window) < window:
            return True
        _last_sent[title] = now
        return False


def _webhook_url() -> str:
    return (os.getenv("ALERT_WEBHOOK_URL") or os.getenv("SLACK_WEBHOOK_URL") or "").strip()


def _write_alert_file(payload: dict[str, Any]) -> None:
    try:
        _ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _ALERT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug("alert file failed: %s", exc)


def send_alert(
    title: str,
    *,
    severity: str = "warning",
    detail: dict[str, Any] | None = None,
    dedupe_seconds: float = _DEDUPE_SECONDS,
) -> bool:
    """Alerta: grava em deploy/alerts.log e entrega o webhook noutro fio (nunca bloqueia quem chama).

    O mesmo título só sai uma vez por `dedupe_seconds` (0 desliga: quem já deduplica por episódio).
    """
    if _duplicate(title, dedupe_seconds):
        return True
    payload = {
        "text": f"[Diomika/{severity}] {title}",
        "severity": severity,
        "title": title,
        "detail": detail or {},
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    logger.warning("ALERT %s: %s %s", severity, title, detail or {})
    _write_alert_file(payload)

    url = _webhook_url()
    if url:
        _pool.submit(_post_webhook, url, payload)
    return True


def webhook_request(url: str, payload: dict[str, Any]) -> tuple[bytes, dict[str, str]]:
    """O corpo e os cabeçalhos do aviso. ntfy mostra o corpo tal e qual: texto legível e `Title`/`Priority`
    (antes chegava o JSON cru, DEVOPS-12); os outros webhooks (Slack, etc.) continuam a receber JSON."""
    host = (urlparse(url).hostname or "").lower()
    if host == "ntfy.sh" or host.startswith("ntfy."):
        lines = [f"{k}: {v}" for k, v in (payload.get("detail") or {}).items()]
        priority = {"critical": "urgent", "error": "high"}.get(str(payload.get("severity")), "default")
        headers = {"Title": str(payload.get("title", "Diomika"))[:250], "Priority": priority, "Content-Type": "text/plain; charset=utf-8"}
        return ("\n".join(lines) or str(payload.get("text", ""))).encode("utf-8"), headers
    return json.dumps(payload).encode("utf-8"), {"Content-Type": "application/json"}


def _post_webhook(url: str, payload: dict[str, Any]) -> None:
    try:
        from core.ssrf_guard import assert_safe_outbound_url

        assert_safe_outbound_url(url)
    except Exception as exc:
        logger.error("ALERT webhook URL rejeitada pelo SSRF guard: %s", exc)
        return

    try:
        data, headers = webhook_request(url, payload)
        req = urllib.request.Request(url, data=data, method="POST", headers=headers)
        with urllib.request.urlopen(req, timeout=8):
            pass
    except Exception as exc:
        logger.debug("alert webhook failed: %s", exc)


def alert_if(condition: bool, title: str, **detail: Any) -> None:
    if condition:
        send_alert(title, severity="critical", detail=detail)


def webhook_configured() -> bool:
    return bool(_webhook_url())
