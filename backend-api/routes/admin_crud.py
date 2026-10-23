"""CRUD genérico para backoffice web — validação via TABLE_MAP.

Esquema unificado: os nomes de tabela na URL (table_name) continuam a ser os
"nomes virtuais" de sempre (ex.: "almofada", "modelos_almofadas") — o
backoffice e as rotas não mudam. Internamente resolvem para 1 de 3 tabelas
físicas partilhadas (product_models / product_variants / product_model_colors)
através de physical_table_for()/tipo_for_table(), com o filtro `tipo_catalogo`
aplicado onde é preciso distinguir uma família da outra (listas, criação).
Uma pesquisa por `id` não precisa do filtro — o id já é único na tabela toda.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile

from core.auth import Role, SENSITIVE_BUSINESS_TABLES, assert_table_action, require_admin
from core.cqrs.commands.catalog import soft_delete
from core.database import get_db
from core.idempotency import (
    IdempotencyUnavailable,
    abort_idempotent_request,
    begin_idempotent_request,
    complete_idempotent_request,
    get_cached_response,
)
from core.local_only import admin_must_be_local
from models.catalog_registry import (
    admin_list_select_query,
    all_colors_tables,
    all_model_tables,
    all_product_tables,
    colors_table_for_model_table,
    colors_table_for_tipo,
    fold_attributes,
    list_select_query,
    relation_options_select_query,
    tipo_for_table,
)
from models.catalog_attributes import CATEGORY_ATTRIBUTE_SCHEMAS
from models.schemas import PRODUCT_MODELS_TABLE, TABLE_MAP
from utils.image_urls import content_type_for_path
from utils.image_validation import validate_upload_bytes
from utils.postgrest_filter import or_literal
from utils.storage import upload_bytes

from .admin_crud_helpers import (
    _allowed_upload_field,
    _attr,
    _audit,
    _client_error,
    _db_table,
    _invalidate_catalog_cache,
    _is_expected_client_conflict,
    _normalize_payload,
    _resolve_image_fields,
    _role,
    _schedule_barcode_update,
    _schema_for,
    _scoped,
)
from .admin_crud_publishing import (
    _cascade_category_visibility,
    _hide_catalog_children,
    _publish_catalog_children,
)
from .admin_crud_validation import (
    _assert_model_category_tipo,
    _assert_model_publishable,
    _product_validation_table,
    _validate_product_payload,
)

logger = logging.getLogger("diomika-api")

router = APIRouter(
    prefix="/admin/crud",
    tags=["Admin CRUD"],
    dependencies=[Depends(admin_must_be_local), Depends(require_admin)],
)



@router.post("/upload-image")
async def upload_image(
    request: Request,
    table: str,
    field: str,
    file: UploadFile = File(...),
    role: Role = Depends(require_admin),
):
    """Upload multipart — para backoffice Vue (browser não envia paths locais)."""
    if not _allowed_upload_field(table, field):
        raise HTTPException(status_code=400, detail="Campo de imagem inválido para esta categoria.")
    assert_table_action(table, "upload", role)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Ficheiro em falta")
    ext = Path(file.filename).suffix.lower() or ".png"
    dest = f"{table}/{field}/{uuid4().hex}{ext}"
    data = await file.read()
    try:
        validate_upload_bytes(data, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ctype = file.content_type or content_type_for_path(file.filename)
    url = upload_bytes(data, dest, ctype)
    _audit(request, "upload", table, detail={"field": field, "bytes": len(data)})
    return {"url": url}


def relation_options(
    table_name: str,
    *,
    visible_only: bool = False,
    limit: int = 200,
    id_modelo: str | None = None,
) -> list[dict]:
    """Opções de dropdown (id + label) de uma tabela. Função separada da rota
    para o formulário agregado (routes/admin_form.py) poder juntar várias
    tabelas numa só resposta, em vez de uma chamada HTTP por relação."""
    limit = min(max(limit, 1), 300)
    query = _scoped(_db_table(table_name).select(relation_options_select_query(table_name)), table_name, use_join=True)
    if visible_only:
        query = query.eq("visibilidade", True)
    if id_modelo and table_name in (*all_colors_tables(), *all_product_tables()):
        query = query.eq("id_modelo", id_modelo)
    try:
        res = query.order("nome").limit(limit).execute()
    except Exception:
        try:
            res = query.order("created_at", desc=True).limit(limit).execute()
        except Exception:
            res = query.limit(limit).execute()
    rows = res.data or []

    def _label(row: dict) -> str:
        if row.get("nome"):
            return str(row["nome"]).strip()
        if row.get("ean"):
            return str(row["ean"]).strip()
        if row.get("numero") is not None:
            parts = [str(row["numero"]).strip()]
            if row.get("nome"):
                parts.append(str(row["nome"]).strip())
            return " · ".join(p for p in parts if p)
        return str(row.get("id", ""))[:8]

    return [
        {
            "id": r["id"],
            "label": _label(r) or str(r.get("id", ""))[:8],
            **({"tipo_catalogo": r["tipo_catalogo"]} if table_name == "categories" and r.get("tipo_catalogo") else {}),
        }
        for r in rows
    ]


@router.get("/{table_name}/options")
def list_relation_options(
    request: Request,
    table_name: str,
    visible_only: bool = False,
    limit: int = 200,
    id_modelo: str | None = None,
):
    """Dropdowns leves — só id + label, sem embeds pesados."""
    _schema_for(table_name)
    assert_table_action(table_name, "read", _role(request))
    return {
        "items": relation_options(
            table_name, visible_only=visible_only, limit=limit, id_modelo=id_modelo
        )
    }


@router.get("/{table_name}")
def list_records(
    request: Request,
    table_name: str,
    visible_only: bool = False,
    limit: int = 100,
    offset: int = 0,
    id_modelo: str | None = None,
    q: str | None = None,
):
    _schema_for(table_name)
    assert_table_action(table_name, "read", _role(request))
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    select_q = admin_list_select_query(table_name, embed_category=table_name in all_product_tables())
    query = _scoped(_db_table(table_name).select(select_q), table_name, use_join=True)
    if visible_only:
        query = query.eq("visibilidade", True)
    if id_modelo and table_name in (*all_colors_tables(), *all_product_tables()):
        query = query.eq("id_modelo", id_modelo)
    needle = (q or "").strip()
    if needle:
        pattern = or_literal(f"%{needle}%")
        if table_name in all_product_tables():
            tipo = tipo_for_table(table_name) or ""
            variant_attrs = (CATEGORY_ATTRIBUTE_SCHEMAS.get(tipo) or {}).get("variant_attributes") or {}
            terms = [f"ean.ilike.{pattern}"]
            for attr_name in ("dimensoes", "altura"):
                if attr_name in variant_attrs:
                    terms.append(f"attributes->>{attr_name}.ilike.{pattern}")
            query = query.or_(",".join(terms))
        elif table_name in all_model_tables():
            query = query.or_(f"nome.ilike.{pattern},slug.ilike.{pattern}")
        elif table_name == "categories":
            query = query.or_(f"nome.ilike.{pattern},slug.ilike.{pattern}")
    try:
        res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    except TypeError:
        try:
            res = query.order("created_at", ascending=False).range(offset, offset + limit - 1).execute()
        except Exception:
            res = query.limit(limit).offset(offset).execute()
    except Exception:
        res = query.limit(limit).execute()
    rows = res.data or []
    return {"items": rows, "limit": limit, "offset": offset, "count": len(rows)}


@router.get("/{table_name}/{record_id}")
def get_record(request: Request, table_name: str, record_id: str):
    _schema_for(table_name)
    assert_table_action(table_name, "read", _role(request))
    res = (
        _scoped(_db_table(table_name).select(list_select_query(table_name)), table_name, use_join=True)
        .eq("id", record_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Registo não encontrado")
    return res.data[0]


@router.post("/{table_name}")
def create_record(
    request: Request,
    table_name: str,
    body: dict,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    schema_class = _schema_for(table_name)
    assert_table_action(table_name, "create", _role(request))
    body = fold_attributes(table_name, body)
    key = (idempotency_key or "").strip()
    op = _idempotency_op(table_name, body)
    if key:
        try:
            state = begin_idempotent_request(key, op)
        except IdempotencyUnavailable:
            raise HTTPException(status_code=503, detail="Idempotência indisponível.") from None
        if state == "cached":
            cached = get_cached_response(key, op)
            if cached:
                return cached
        if state == "in_progress":
            raise HTTPException(status_code=409, detail="Pedido em processamento — aguarde.")
        if state == "unavailable":
            raise HTTPException(status_code=503, detail="Idempotência indisponível.")
    try:
        body = _resolve_image_fields(table_name, body)
        body = _enrich_create_payload(table_name, body)
        validated = schema_class(**body)
        payload = _normalize_payload(validated.model_dump())
        ins = _db_table(table_name).insert(payload).execute()
        row = (ins.data or [{}])[0]
        record_id = str(row.get("id") or "")
        if key:
            complete_idempotent_request(key, op, row)
        _invalidate_catalog_cache(table_name=table_name, record=row, record_id=record_id)
        _audit(request, "create", table_name, resource_id=record_id or None)
        _schedule_barcode_update(table_name, record_id, payload.get("ean"))
        if payload.get("visibilidade") and table_name in all_model_tables():
            _publish_catalog_children(table_name, record_id)
        return row
    except HTTPException:
        if key:
            abort_idempotent_request(key, op)
        raise
    except Exception as exc:
        if key:
            abort_idempotent_request(key, op)
        detail = _client_error(exc)
        if _is_expected_client_conflict(exc):
            logger.warning("Create %s: %s", table_name, detail)
            raise HTTPException(status_code=409, detail=detail) from exc
        logger.error("Create %s: %s", table_name, exc)
        raise HTTPException(status_code=400, detail=detail) from exc


@router.put("/{table_name}/{record_id}")
def update_record(request: Request, table_name: str, record_id: str, body: dict):
    schema_class = _schema_for(table_name)
    assert_table_action(table_name, "update", _role(request))
    try:
        body = fold_attributes(table_name, {**body, "id": record_id})
        body = _resolve_image_fields(table_name, body)
        body = _enrich_update_payload(table_name, body, record_id)
        validated = schema_class(**body)
        payload = _normalize_payload(validated.model_dump())
        payload.pop("id", None)
        payload.pop("created_at", None)
        res = _scoped(_db_table(table_name).update(payload), table_name).eq("id", record_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Registo não encontrado")
        updated = res.data[0]
        _invalidate_catalog_cache(table_name=table_name, record={**payload, **updated}, record_id=record_id)
        _audit(request, "update", table_name, resource_id=record_id)
        _schedule_barcode_update(table_name, record_id, payload.get("ean"))
        if payload.get("visibilidade") and table_name in all_model_tables():
            _publish_catalog_children(table_name, record_id)
        if table_name == "categories":
            if "visibilidade" in payload:
                _cascade_category_visibility(record_id, bool(payload.get("visibilidade")))
        return updated
    except HTTPException:
        raise
    except Exception as exc:
        detail = _client_error(exc)
        if _is_expected_client_conflict(exc):
            logger.warning("Update %s/%s: %s", table_name, record_id, detail)
            raise HTTPException(status_code=409, detail=detail) from exc
        logger.error("Update %s/%s: %s", table_name, record_id, exc)
        raise HTTPException(status_code=400, detail=detail) from exc


@router.patch("/{table_name}/{record_id}/visibility")
def patch_visibility(request: Request, table_name: str, record_id: str, body: dict):
    """Alterna visibilidade sem revalidar o registo completo."""
    _schema_for(table_name)
    assert_table_action(table_name, "update", _role(request))
    if "visibilidade" not in body:
        raise HTTPException(status_code=400, detail="Campo visibilidade em falta")
    vis = bool(body["visibilidade"])
    if vis and table_name in all_model_tables():
        try:
            _assert_model_publishable(table_name, record_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    res = _scoped(_db_table(table_name).update({"visibilidade": vis}), table_name).eq("id", record_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Registo não encontrado")
    if table_name in all_model_tables():
        if vis:
            _publish_catalog_children(table_name, record_id)
        else:
            _hide_catalog_children(table_name, record_id)
    elif table_name == "categories":
        _cascade_category_visibility(record_id, vis)
    _invalidate_catalog_cache(table_name=table_name, record=res.data[0], record_id=record_id)
    _audit(request, "visibility", table_name, resource_id=record_id, visibilidade=vis)
    return (res.data or [{"id": record_id, "visibilidade": vis}])[0]


@router.post("/{table_name}/{record_id}/publish")
def publish_record(request: Request, table_name: str, record_id: str):
    """Torna o registo visível na loja (e cores/produtos do modelo, se aplicável)."""
    cfg = TABLE_MAP.get(table_name)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Tabela «{table_name}» não registada no catálogo")
    assert_table_action(table_name, "update", _role(request))
    if table_name in all_model_tables():
        try:
            _assert_model_publishable(table_name, record_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    res = _scoped(_db_table(table_name).update({"visibilidade": True}), table_name).eq("id", record_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Registo não encontrado")

    if table_name in all_model_tables():
        _publish_catalog_children(table_name, record_id)
    elif table_name == "categories":
        _cascade_category_visibility(record_id, True)

    _invalidate_catalog_cache(table_name=table_name, record=res.data[0], record_id=record_id)
    _audit(request, "publish", table_name, resource_id=record_id)
    return (res.data or [{"id": record_id, "visibilidade": True}])[0]


@router.patch("/{table_name}/{record_id}/lida")
def patch_lida(request: Request, table_name: str, record_id: str, body: dict):
    """Marca orçamento/mensagem como lida ou não lida."""
    _schema_for(table_name)
    assert_table_action(table_name, "update", _role(request))
    if table_name not in ("pedidos_orcamento", "contact_messages"):
        raise HTTPException(status_code=400, detail="Campo lida não aplicável a esta tabela")
    if "lida" not in body:
        raise HTTPException(status_code=400, detail="Campo lida em falta")
    lida = bool(body["lida"])
    res = _db_table(table_name).update({"lida": lida}).eq("id", record_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Registo não encontrado")
    _audit(request, "mark_read", table_name, resource_id=record_id, lida=lida)
    return (res.data or [{"id": record_id, "lida": lida}])[0]


@router.delete("/{table_name}/{record_id}")
def delete_record(request: Request, table_name: str, record_id: str, hard: bool = False):
    _schema_for(table_name)
    if hard and table_name in SENSITIVE_BUSINESS_TABLES:
        hard = False
    action = "hard_delete" if hard else "delete"
    assert_table_action(table_name, action, _role(request))
    try:
        if hard:
            if table_name in all_model_tables():
                get_db().table("product_model_colors").delete().eq("id_modelo", record_id).execute()
                get_db().table("product_variants").delete().eq("id_modelo", record_id).execute()
            _scoped(_db_table(table_name).delete(), table_name).eq("id", record_id).execute()
            _invalidate_catalog_cache(table_name=table_name, record_id=record_id)
            _audit(request, "hard_delete", table_name, resource_id=record_id)
            return {"status": "deleted", "hard": True}
        result = soft_delete(table_name, record_id)
        _invalidate_catalog_cache(table_name=table_name, record_id=record_id)
        _audit(request, "soft_delete", table_name, resource_id=record_id)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Delete %s/%s: %s", table_name, record_id, exc)
        raise HTTPException(status_code=400, detail=_client_error(exc)) from exc


def _idempotency_op(table_name: str, payload: dict) -> str:
    """Âmbito da chave de idempotência: operação + hash do corpo do pedido.

    Sem o hash, reutilizar a mesma Idempotency-Key num pedido *diferente*
    devolvia em silêncio a resposta do primeiro pedido. Incluir o hash faz
    pedidos diferentes terem operações diferentes, por isso nunca partilham
    resposta em cache.
    """
    import hashlib

    body_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:24]
    return f"admin_create:{table_name}:{body_hash}"


def _enrich_create_payload(table_name: str, body: dict) -> dict:
    """Enrich payload before create (e.g., set defaults, computed fields)."""
    return body


def _enrich_update_payload(table_name: str, body: dict, record_id: str) -> dict:
    """Enrich payload before update (e.g., normalize fields)."""
    return body
