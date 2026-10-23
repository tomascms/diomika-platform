"""Manutenção de chaves idempotency expiradas."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from core.database import get_db

logger = logging.getLogger("diomika-idempotency")


def purge_expired_idempotency_keys() -> int:
    """Remove chaves idempotency com expires_at no passado."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    try:
        res = (
            db.table("idempotency_keys")
            .select("key", count="exact")
            .lt("expires_at", now)
            .execute()
        )
        pending = res.count or 0
        if not pending:
            return 0
        db.table("idempotency_keys").delete().lt("expires_at", now).execute()
        logger.info("Idempotency: %s chave(s) expirada(s) removida(s)", pending)
        return pending
    except Exception as exc:
        logger.debug("purge_expired_idempotency_keys: %s", exc)
        return 0
