"""Manutenção de sagas — detecta estados zombie."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from core.database import get_db

logger = logging.getLogger("diomika-saga-maintenance")

STALE_MINUTES = 30


def sweep_zombie_sagas(max_age_minutes: int = STALE_MINUTES) -> int:
    """Marca sagas 'running' antigas como failed_stale."""
    db = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)).isoformat()
    try:
        res = (
            db.table("saga_instances")
            .select("id, saga_type, current_step, status, updated_at")
            .eq("status", "running")
            .lt("updated_at", cutoff)
            .execute()
        )
        rows = res.data or []
    except Exception as exc:
        logger.debug("sweep_zombie_sagas: %s", exc)
        return 0

    fixed = 0
    for row in rows:
        sid = row.get("id")
        if not sid:
            continue
        try:
            db.table("saga_instances").update(
                {
                    "status": "failed_stale",
                    "current_step": row.get("current_step") or "unknown",
                    "context": {
                        **(row.get("context") or {}),
                        "swept_at": datetime.now(timezone.utc).isoformat(),
                        "reason": f"running > {max_age_minutes}min",
                    },
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", sid).execute()
            fixed += 1
            logger.warning("Saga zombie corrigida: %s (%s)", sid[:8], row.get("saga_type"))
        except Exception as exc:
            logger.error("Falha ao corrigir saga %s: %s", sid, exc)
    return fixed
