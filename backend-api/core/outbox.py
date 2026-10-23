"""Outbox pattern — eventos pendentes para retry assíncrono."""
from __future__ import annotations

import logging
import os
import socket
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from core.database import get_db
from core.resilience import log_dlq_event

logger = logging.getLogger("diomika-outbox")

_STALE_PROCESSING_MINUTES = int(os.getenv("OUTBOX_STALE_MINUTES", "15"))
_WORKER_ID = os.getenv("OUTBOX_WORKER_ID") or f"{socket.gethostname()}-{os.getpid()}"


def enqueue_event(event_type: str, payload: dict[str, Any], max_attempts: int = 5) -> str:
    event_id = str(uuid4())
    db = get_db()
    try:
        db.table("outbox_events").insert(
            {
                "id": event_id,
                "event_type": event_type,
                "payload": payload,
                "status": "pending",
                "attempts": 0,
                "max_attempts": max_attempts,
                "next_retry_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
    except Exception as exc:
        logger.warning("Outbox table indisponível, evento em log: %s", exc)
        log_dlq_event(f"OUTBOX_{event_type}", event_id, exc)
    return event_id


def _release_stale_claims() -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=_STALE_PROCESSING_MINUTES)).isoformat()
    db = get_db()
    try:
        db.table("outbox_events").update(
            {"status": "pending", "claimed_by": None, "claimed_at": None}
        ).eq("status", "processing").lt("claimed_at", cutoff).execute()
    except Exception as exc:
        logger.debug("release stale claims: %s", exc)


def try_claim(event_id: str) -> bool:
    """Claim optimista — so processa se status ainda for pending."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    try:
        res = (
            db.table("outbox_events")
            .update({"status": "processing", "claimed_by": _WORKER_ID, "claimed_at": now})
            .eq("id", event_id)
            .eq("status", "pending")
            .execute()
        )
        return bool(res.data)
    except Exception:
        return False


def fetch_pending(limit: int = 20) -> list[dict]:
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    try:
        res = (
            db.table("outbox_events")
            .select("*")
            .eq("status", "pending")
            .lte("next_retry_at", now)
            .order("next_retry_at")
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def claim_pending(limit: int = 20) -> list[dict]:
    """Devolve eventos claimed por este worker (seguro com multiplas replicas)."""
    _release_stale_claims()
    claimed: list[dict] = []
    for event in fetch_pending(limit):
        if try_claim(event["id"]):
            claimed.append({**event, "status": "processing"})
    return claimed


def mark_done(event_id: str) -> None:
    get_db().table("outbox_events").update({"status": "done"}).eq("id", event_id).execute()


def mark_failed(event_id: str, error: str, attempts: int, max_attempts: int) -> None:
    db = get_db()
    if attempts >= max_attempts:
        db.table("outbox_events").update({"status": "failed", "last_error": error, "attempts": attempts}).eq(
            "id", event_id
        ).execute()
        log_dlq_event("OUTBOX_FAILED", event_id, error)
        return
    next_retry = datetime.now(timezone.utc) + timedelta(seconds=min(300, 2**attempts * 10))
    db.table("outbox_events").update(
        {
            "status": "pending",
            "attempts": attempts,
            "last_error": error,
            "next_retry_at": next_retry.isoformat(),
        }
    ).eq("id", event_id).execute()
