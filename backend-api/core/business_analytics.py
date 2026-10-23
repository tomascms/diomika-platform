"""Agregados de negócio para ops / Command Center."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.database import get_db


def _since(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _count(table: str, *, visibilidade: bool | None = True, extra: dict | None = None) -> int:
    q = get_db().table(table).select("id", count="exact")
    if visibilidade is not None:
        q = q.eq("visibilidade", visibilidade)
    for key, val in (extra or {}).items():
        q = q.eq(key, val)
    res = q.execute()
    return int(res.count or 0)


def _count_since(table: str, since_iso: str, *, visibilidade: bool | None = True) -> int:
    q = get_db().table(table).select("id", count="exact").gte("created_at", since_iso)
    if visibilidade is not None:
        q = q.eq("visibilidade", visibilidade)
    res = q.execute()
    return int(res.count or 0)


def build_business_summary() -> dict:
    since_1d = _since(1)
    since_7d = _since(7)

    quotes = {
        "total": _count("pedidos_orcamento"),
        "unread": _count("pedidos_orcamento", extra={"lida": False}),
        "today": _count_since("pedidos_orcamento", since_1d),
        "last7d": _count_since("pedidos_orcamento", since_7d),
    }
    contacts = {
        "total": _count("contact_messages"),
        "unread": _count("contact_messages", extra={"lida": False}),
        "today": _count_since("contact_messages", since_1d),
        "last7d": _count_since("contact_messages", since_7d),
    }
    orders = {
        "total": _count("encomendas_internas"),
        "today": _count_since("encomendas_internas", since_1d),
        "last7d": _count_since("encomendas_internas", since_7d),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quotes": quotes,
        "contacts": contacts,
        "orders": orders,
        "pipeline": {
            "leads_7d": quotes["last7d"] + contacts["last7d"],
            "unread_total": quotes["unread"] + contacts["unread"],
        },
    }
