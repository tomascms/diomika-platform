"""Retenção / minimização de PII — job real, não só documentação."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("diomika-retention")


def _days(name: str, default: int) -> int:
    try:
        return max(30, int(os.getenv(name) or str(default)))
    except ValueError:
        return default


def purge_expired_pii() -> dict[str, int]:
    """Apaga/anonimiza dados antigos conforme política.

    Env:
      RETENTION_CONTACT_DAYS (default 730)
      RETENTION_AUDIT_DAYS (default 365)
      RETENTION_ORCAMENTO_DAYS (default 730) — só status cancelados/antigos
    """
    from core.database import get_db

    db = get_db()
    now = datetime.now(timezone.utc)
    out = {"contact_messages": 0, "admin_audit_log": 0, "pedidos_orcamento": 0}

    contact_cut = (now - timedelta(days=_days("RETENTION_CONTACT_DAYS", 730))).isoformat()
    audit_cut = (now - timedelta(days=_days("RETENTION_AUDIT_DAYS", 365))).isoformat()
    orc_cut = (now - timedelta(days=_days("RETENTION_ORCAMENTO_DAYS", 730))).isoformat()

    try:
        res = db.table("contact_messages").delete().lt("created_at", contact_cut).execute()
        out["contact_messages"] = len(res.data or [])
    except Exception as exc:
        logger.warning("retention contact_messages: %s", exc)

    try:
        res = db.table("admin_audit_log").delete().lt("created_at", audit_cut).execute()
        out["admin_audit_log"] = len(res.data or [])
    except Exception as exc:
        logger.warning("retention admin_audit_log: %s", exc)

    # Orçamentos muito antigos em estados terminais
    try:
        res = (
            db.table("pedidos_orcamento")
            .delete()
            .lt("created_at", orc_cut)
            .in_("status", ["Cancelado", "Arquivado", "Rejeitado"])
            .execute()
        )
        out["pedidos_orcamento"] = len(res.data or [])
    except Exception as exc:
        logger.warning("retention pedidos_orcamento: %s", exc)

    total = sum(out.values())
    if total:
        logger.info("Retention purge: %s", out)
        try:
            from core.alerts import send_alert

            send_alert("Retention purge executado", severity="info", detail=out)
        except Exception:
            pass
    return out
