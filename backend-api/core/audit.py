"""Auditoria de acções admin — Supabase + fallback JSONL local."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import Request

from core.database import get_db
from core.rate_limit import get_client_ip
from paths import BACKEND_ROOT

logger = logging.getLogger("diomika-audit")

_LOG_FILE = BACKEND_ROOT / "logs" / "admin_audit.jsonl"


def _safe_detail(detail: dict[str, Any] | None) -> dict[str, Any]:
    if not detail:
        return {}
    out: dict[str, Any] = {}
    for k, v in detail.items():
        key = str(k).lower()
        if any(s in key for s in ("password", "secret", "token", "api_key", "authorization")):
            out[k] = "[redacted]"
        elif isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v if not isinstance(v, str) or len(v) < 500 else v[:500] + "…"
        else:
            out[k] = str(v)[:200]
    return out


def log_admin_action(
    *,
    action: str,
    resource: str,
    role: str = "admin",
    actor: str | None = None,
    resource_id: str | None = None,
    detail: dict[str, Any] | None = None,
    request_id: str | None = None,
    client_ip: str | None = None,
) -> None:
    """Regista acção sensível (quem/quando/o quê/de onde). Nunca falha o pedido."""
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
        "role": role,
        "actor": actor,
        "request_id": request_id,
        "client_ip": client_ip,
        "detail": _safe_detail(detail),
    }
    try:
        get_db().table("admin_audit_log").insert(
            {
                "action": action,
                "resource": resource,
                "resource_id": resource_id,
                "role": role,
                "actor": actor,
                "request_id": request_id,
                "client_ip": client_ip,
                "detail": payload["detail"],
            }
        ).execute()
    except Exception as exc:
        logger.debug("audit DB skip: %s", exc)
        try:
            _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with _LOG_FILE.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception as file_exc:
            logger.warning("audit file failed: %s", file_exc)


def audit_request(
    request: Request,
    *,
    action: str,
    resource: str,
    resource_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Atalho: preenche actor/role/IP/request_id a partir do Request."""
    log_admin_action(
        action=action,
        resource=resource,
        resource_id=resource_id,
        role=str(getattr(request.state, "api_role", "admin")),
        actor=getattr(request.state, "api_actor", None),
        request_id=getattr(request.state, "request_id", None),
        client_ip=get_client_ip(request),
        detail=detail,
    )
