"""Shared helpers for admin CRUD operations (database, auth, cache, validation)."""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, Request

from core.audit import log_admin_action
from core.cache import invalidate_catalog_change
from core.database import get_db
from core.rate_limit import get_client_ip
from models.catalog_registry import (
    all_colors_tables,
    all_product_tables,
    level_for_table,
    physical_table_for,
    tipo_for_table,
)
from models.schemas import PRODUCT_MODELS_TABLE, TABLE_MAP
from models.ui_schema import get_form_fields
from models.catalog_registry import apply_barcode_on_save
from utils.barcode_gen import apply_barcode_url

logger = logging.getLogger("diomika-api")


# --- Database & scope helpers ---

def _db_table(table_name: str):
    """Get database table handle, resolving virtual to physical table."""
    return get_db().table(physical_table_for(table_name))


def _scoped(query, table_name: str, use_join: bool = False):
    """Filter by catalog family (tipo_catalogo), optionally via parent model join.

    Args:
        query: PostgREST query builder
        table_name: table name (virtual or physical)
        use_join: if True and table is colors, filter via PRODUCT_MODELS_TABLE join
    """
    tipo = tipo_for_table(table_name)
    if not tipo:
        return query

    is_colors = level_for_table(table_name) == "colors"
    if is_colors and use_join:
        return query.eq(f"{PRODUCT_MODELS_TABLE}.tipo_catalogo", tipo)
    elif is_colors:
        return query
    return query.eq("tipo_catalogo", tipo)


def _schema_for(table: str):
    """Get schema for a table, raising 404 if not found."""
    if table not in TABLE_MAP:
        raise HTTPException(status_code=404, detail=f"Tabela «{table}» não registada no catálogo")
    schema = TABLE_MAP[table].get("schema")
    if not schema:
        raise HTTPException(status_code=404, detail="Sem schema")
    return schema


# --- Auth & audit helpers ---

def _role(request: Request):
    """Extract role from request state."""
    from core.auth import Role
    return getattr(request.state, "api_role", "admin")  # type: ignore[return-value]


def _audit(request: Request, action: str, resource: str, resource_id: str | None = None, **detail):
    """Log admin action for audit trail."""
    role = getattr(request.state, "api_role", "admin")
    log_admin_action(
        action=action,
        resource=resource,
        resource_id=resource_id,
        role=str(role),
        actor=getattr(request.state, "api_actor", None),
        request_id=getattr(request.state, "request_id", None),
        client_ip=get_client_ip(request),
        detail=detail or None,
    )


def _normalize_payload(payload: dict) -> dict:
    """Convert UUIDs to strings in payload."""
    out = dict(payload)
    for k, v in list(out.items()):
        if isinstance(v, UUID):
            out[k] = str(v)
    return out


# --- Cache helpers ---

def _invalidate_catalog_cache(*, table_name: str | None = None, record: dict | None = None, record_id: str | None = None) -> None:
    """Invalidate catalog cache after CRUD operation."""
    invalidate_catalog_change(table_name=table_name, record=record, record_id=record_id)


# --- Attribute helpers ---

def _attr(payload: dict, name: str):
    """Get nested attribute value."""
    return (payload.get("attributes") or {}).get(name)


# --- Error handling ---

def _client_error(exc: Exception) -> str:
    """Convert exception to user-friendly error message."""
    from pydantic import ValidationError

    if isinstance(exc, ValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        msg = first.get("msg") or str(exc)
        loc = first.get("loc") or ()
        if loc:
            field = ".".join(str(x) for x in loc if x != "__root__")
            if field:
                return f"{field}: {msg}"
        return str(msg)
    text = str(exc).strip()
    if "duplicate key" in text.lower() or "23505" in text:
        if "assento_id_modelo_key" in text or "assento_modelo_altura" in text or "variant_modelo_altura" in text:
            return "Já existe um assento com esta altura neste modelo."
        if "modelo_cores_model_numero" in text or "model_colors_numero" in text.lower():
            return "Já existe esta cor (número) neste modelo."
        if "ean" in text.lower():
            return "Este EAN já existe noutro produto."
        return "Registo duplicado — já existe um com a mesma chave única."
    if text and text not in ("", "None"):
        return text[:240]
    return "Dados inválidos ou em conflito."


def _is_expected_client_conflict(exc: Exception) -> bool:
    """Check if exception is an expected conflict (duplicate key, etc)."""
    text = str(exc).lower()
    return "duplicate key" in text or "23505" in text or "violates unique" in text


# --- Image handling ---

def _allowed_upload_field(table: str, field: str) -> bool:
    """Check if a field is allowed for image upload."""
    if table not in TABLE_MAP:
        return False
    cfg = TABLE_MAP[table]
    schema = cfg.get("schema")
    if not schema:
        return False
    for field_def in get_form_fields(schema, cfg, table):
        if field_def["name"] == field and field_def.get("widget") in ("image", "multi_image"):
            return True
    return False


def _resolve_image_fields(table_name: str, payload: dict) -> dict:
    """Resolve and upload local image paths before validation."""
    from utils.image_urls import resolve_image_value, resolve_image_list

    out = dict(payload)
    cfg = TABLE_MAP.get(table_name, {})
    schema = cfg.get("schema")
    if not schema:
        return out

    for field_def in get_form_fields(schema, cfg):
        name = field_def["name"]
        if name not in out or out[name] in (None, ""):
            continue
        widget = field_def.get("widget")
        if widget == "image":
            val = str(out[name]).strip()
            if val and not val.startswith(("http://", "https://")):
                out[name] = resolve_image_value(val, table_name, name)
        elif widget == "multi_image":
            raw = out[name]
            if isinstance(raw, str):
                raw = [p.strip() for p in raw.split(";") if p.strip()]
            if isinstance(raw, list):
                out[name] = resolve_image_list([str(v) for v in raw], table_name, name)
    return out


# --- Barcode scheduling ---

def _schedule_barcode_update(table_name: str, record_id: str, ean: str | None) -> None:
    """Generate barcode in background to avoid upload timeout."""
    code = (ean or "").strip()
    if not code or not apply_barcode_on_save(table_name):
        return

    def _job() -> None:
        try:
            payload = {"ean": code}
            apply_barcode_url(payload)
            url = payload.get("barcode_url")
            if url:
                _db_table(table_name).update({"barcode_url": url}).eq("id", record_id).execute()
        except Exception as exc:
            logger.warning("Barcode async %s/%s: %s", table_name, record_id, exc)

    threading.Thread(target=_job, daemon=True).start()
