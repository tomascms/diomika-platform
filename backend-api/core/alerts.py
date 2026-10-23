"""Alertas operacionais — webhook validado (SSRF) + ficheiro local."""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import PROJECT_ROOT

logger = logging.getLogger("diomika-alerts")

_ALERT_LOG = Path(os.getenv("ALERT_LOG_FILE") or (PROJECT_ROOT / "deploy" / "alerts.log"))


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
) -> bool:
    """Envia alerta. Sempre grava em deploy/alerts.log; webhook se configurado e safe."""
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
    if not url:
        return True
    try:
        from core.ssrf_guard import assert_safe_outbound_url

        assert_safe_outbound_url(url)
    except Exception as exc:
        logger.error("ALERT webhook URL rejeitada pelo SSRF guard: %s", exc)
        return True

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:
        logger.debug("alert webhook failed: %s", exc)
        return True


def alert_if(condition: bool, title: str, **detail: Any) -> None:
    if condition:
        send_alert(title, severity="critical", detail=detail)


def webhook_configured() -> bool:
    return bool(_webhook_url())
