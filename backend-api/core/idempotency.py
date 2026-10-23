"""Idempotência — evita duplicados em retries e transacções canceladas."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from core.database import get_db
from core.resilience import log_idempotency

logger = logging.getLogger("diomika-api")

_STALE_PROCESSING_SECONDS = 30


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _fetch_idempotency_row(key: str, operation: str) -> dict | None:
    db = get_db()
    res = (
        db.table("idempotency_keys")
        .select("response, created_at")
        .eq("key", key)
        .eq("operation", operation)
        .limit(1)
        .execute()
    )
    data = getattr(res, "data", None) or []
    if not data:
        return None
    row = data[0] if isinstance(data, list) else data
    return row if isinstance(row, dict) else None


def _clear_stale_processing(key: str, operation: str) -> bool:
    row = _fetch_idempotency_row(key, operation)
    if not row:
        return False
    response = row.get("response") or {}
    if not isinstance(response, dict) or not response.get("_processing"):
        return False
    created = _parse_ts(row.get("created_at"))
    if created:
        age = (datetime.now(timezone.utc) - created).total_seconds()
        if age < _STALE_PROCESSING_SECONDS:
            return False
    abort_idempotent_request(key, operation)
    logger.info("idempotency stale lock cleared key=%s op=%s", key, operation)
    return True

ProcessingState = Literal["proceed", "cached", "in_progress", "unavailable"]

_PROCESSING = {"_processing": True}


class IdempotencyUnavailable(Exception):
    """Base de dados indisponível — fail-closed em produção."""


def _expires_at() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()


def _row_response(res: Any) -> dict | None:
    """Extrai response de select limit(1) / maybe_single (client pode devolver None)."""
    if res is None:
        return None
    data = getattr(res, "data", None)
    if not data:
        return None
    row = data[0] if isinstance(data, list) else data
    if not isinstance(row, dict):
        return None
    response = row.get("response") or {}
    return response if isinstance(response, dict) else None


def get_cached_response(key: str, operation: str) -> dict | None:
    if not key:
        return None
    db = get_db()
    try:
        # limit(1) em vez de maybe_single(): em postgrest recente 0 rows
        # pode devolver res=None / AttributeError em vez de data=None.
        res = (
            db.table("idempotency_keys")
            .select("response")
            .eq("key", key)
            .eq("operation", operation)
            .limit(1)
            .execute()
        )
        response = _row_response(res)
        if not response:
            return None
        if response.get("_processing"):
            return None
        log_idempotency(operation, key)
        return response
    except Exception as exc:
        err = str(exc).lower()
        if "0 rows" in err or "pgrst116" in err or "nonetype" in err:
            return None
        logger.error("idempotency read failed key=%s op=%s: %s", key, operation, exc)
        raise IdempotencyUnavailable("Idempotência indisponível") from exc


def begin_idempotent_request(key: str, operation: str) -> ProcessingState:
    """Reserva a chave antes do side-effect. Retorna cached se já concluído."""
    if not key:
        return "proceed"

    try:
        cached = get_cached_response(key, operation)
    except IdempotencyUnavailable:
        return "unavailable"
    if cached:
        return "cached"

    db = get_db()
    try:
        db.table("idempotency_keys").insert(
            {
                "key": key,
                "operation": operation,
                "response": _PROCESSING,
                "expires_at": _expires_at(),
            }
        ).execute()
        return "proceed"
    except Exception as insert_exc:
        logger.debug("idempotency insert race key=%s: %s", key, insert_exc)

    try:
        res = (
            db.table("idempotency_keys")
            .select("response")
            .eq("key", key)
            .eq("operation", operation)
            .limit(1)
            .execute()
        )
        response = _row_response(res) or {}
        if response.get("_processing"):
            if _clear_stale_processing(key, operation):
                return "proceed"
            return "in_progress"
        if response:
            log_idempotency(operation, key)
            return "cached"
    except Exception as exc:
        err = str(exc).lower()
        if "0 rows" in err or "pgrst116" in err or "nonetype" in err:
            return "in_progress"
        logger.error("idempotency state read failed key=%s op=%s: %s", key, operation, exc)
        return "unavailable"
    return "in_progress"


def complete_idempotent_request(key: str, operation: str, response: Any) -> None:
    if not key:
        return
    db = get_db()
    payload = response if isinstance(response, dict) else {"result": response}
    try:
        db.table("idempotency_keys").upsert(
            {
                "key": key,
                "operation": operation,
                "response": payload,
                "expires_at": _expires_at(),
            }
        ).execute()
    except Exception as exc:
        logger.warning("idempotency complete failed key=%s op=%s: %s", key, operation, exc)


def abort_idempotent_request(key: str, operation: str) -> None:
    """Liberta chave se a operação falhou antes de persistir dados."""
    if not key:
        return
    db = get_db()
    try:
        db.table("idempotency_keys").delete().eq("key", key).eq("operation", operation).execute()
    except Exception as exc:
        logger.warning("idempotency abort failed key=%s op=%s: %s", key, operation, exc)
