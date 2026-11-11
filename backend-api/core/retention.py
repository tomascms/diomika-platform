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


def _flag(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in ("1", "true", "yes", "on")


def purge_expired_pii() -> dict[str, int]:
    """Apaga/anonimiza dados antigos conforme política.

    Env:
      RETENTION_CONTACT_DAYS (default 730)
      RETENTION_AUDIT_DAYS (default 365)
      RETENTION_ORCAMENTO_DAYS (default 730)
      RETENTION_ORCAMENTO_AGE_PURGE=1 liga a purga por idade dos pedidos sem venda (LEGAL-09): o aviso de
        privacidade promete 24 meses para pedidos sem venda. Fica desligada por omissão até o backoffice
        poder marcar uma venda (tarefa 2.7): sem isso, `vendido_em` está sempre vazio e apagava vendas.
      RETENTION_OUTBOX_DAYS / RETENTION_SAGA_DAYS (default 30, mínimo 30): cópias técnicas dos emails.
    """
    from core.database import get_db

    db = get_db()
    now = datetime.now(timezone.utc)
    out = {"contact_messages": 0, "admin_audit_log": 0, "pedidos_orcamento": 0, "outbox_events": 0, "saga_instances": 0}

    def cut(name: str, default: int) -> str:
        return (now - timedelta(days=_days(name, default))).isoformat()

    contact_cut = cut("RETENTION_CONTACT_DAYS", 730)
    audit_cut = cut("RETENTION_AUDIT_DAYS", 365)
    orc_cut = cut("RETENTION_ORCAMENTO_DAYS", 730)

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

    # Orçamentos: nunca os que acabaram em venda (vendido_em preenchido). Sem a purga por idade ligada,
    # só os que alguém marcou como terminais.
    try:
        query = db.table("pedidos_orcamento").delete().lt("created_at", orc_cut).is_("vendido_em", "null")
        if not _flag("RETENTION_ORCAMENTO_AGE_PURGE"):
            query = query.in_("status", ["Cancelado", "Arquivado", "Rejeitado"])
        res = query.execute()
        out["pedidos_orcamento"] = len(res.data or [])
    except Exception as exc:
        logger.warning("retention pedidos_orcamento: %s", exc)

    # Cópias técnicas do corpo dos emails (nome, email, telefone, texto): só as concluídas ou falhadas de vez.
    try:
        res = (
            db.table("outbox_events")
            .delete()
            .lt("created_at", cut("RETENTION_OUTBOX_DAYS", 30))
            .in_("status", ["done", "failed"])
            .execute()
        )
        out["outbox_events"] = len(res.data or [])
    except Exception as exc:
        logger.warning("retention outbox_events: %s", exc)

    try:
        res = (
            db.table("saga_instances")
            .delete()
            .lt("updated_at", cut("RETENTION_SAGA_DAYS", 30))
            .neq("status", "running")
            .execute()
        )
        out["saga_instances"] = len(res.data or [])
    except Exception as exc:
        logger.warning("retention saga_instances: %s", exc)

    total = sum(out.values())
    if total:
        logger.info("Retention purge: %s", out)
        try:
            from core.alerts import send_alert

            send_alert("Retention purge executado", severity="info", detail=out)
        except Exception:
            pass
    return out
