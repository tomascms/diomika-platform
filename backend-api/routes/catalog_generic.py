"""Rotas genéricas de catálogo — uma URL por tipo registado em CATALOG_TYPES.

Esquema unificado: a lista "merged" do backoffice (todas as categorias juntas)
deixou de precisar de um fan-out paralelo a N tabelas físicas + merge/sort em
memória — é 1 query paginada no servidor à tabela única, com `tipo_catalogo`
como filtro opcional."""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from core.auth import require_catalog_role
from core.cache import catalog_cache_ttl, catalog_version, get_or_set
from core.catalog_service import catalogue_for_category, model_detail_for_slugs, model_detail_for_tipo
from core.catalog_storefront import DEFAULT_PAGE_LIMIT
from core.database import get_db
from core.local_only import admin_must_be_local
from models.catalog_registry import (
    CATALOG_TYPES,
    admin_merged_select_query,
    is_valid_storefront_tipo,
    is_valid_tipo,
    tipo_label,
)
from models.catalog_views import is_catalog_view
from models.schemas import PRODUCT_MODELS_TABLE, PRODUCT_VARIANTS_TABLE, aggregated_tipos_for_tipo

logger = logging.getLogger("diomika-api")

router = APIRouter(prefix="/catalogo", tags=["Catálogo"])


@router.get("/meta")
async def get_catalog_meta():
    """Tipos, tabelas e modos de vitrine — derivado de CATALOG_TYPES."""
    from models.catalog_registry import catalog_metadata

    ttl = catalog_cache_ttl()
    return await asyncio.to_thread(get_or_set, "catalog:meta", float(ttl), catalog_metadata)


@router.get("/version")
async def get_catalog_version():
    """Muda a cada escrita no backoffice — a cache da loja na Cloudflare usa-a na chave."""
    value = await asyncio.to_thread(catalog_version)
    return JSONResponse({"v": value}, headers={"Cache-Control": "no-store"})


@router.get("/search")
async def search_catalog(q: str = "", limit: int = 40):
    """Pesquisa modelos por nome, slug ou EAN — substitui preload total no cliente."""
    from core.catalog_search import search_storefront

    needle = (q or "").strip()
    if len(needle) < 2:
        return []
    lim = min(max(limit, 1), 80)
    cache_key = f"catalog:search:{needle.lower()}:{lim}"
    ttl = catalog_cache_ttl()

    def load():
        return search_storefront(needle, limit=lim)

    try:
        return await asyncio.to_thread(get_or_set, cache_key, float(ttl), load)
    except Exception as exc:
        logger.error("Search catalogo %r: %s", needle, exc)
        raise HTTPException(status_code=500, detail="Erro na pesquisa") from exc


def _require_tipo(tipo: str) -> dict:
    if not is_valid_storefront_tipo(tipo):
        raise HTTPException(status_code=404, detail=f"Tipo «{tipo}» não registado.")
    if is_valid_tipo(tipo):
        return CATALOG_TYPES[tipo]
    return {"label": tipo, "storefront_mode": "aggregado"}


@router.get("/modelo-detalhe/{id_modelo}")
async def get_storefront_model_detail_auto(id_modelo: str):
    """Detalhe de modelo — deteta o tipo automaticamente (URLs legadas da loja).

    Esquema unificado: o tipo já é uma coluna no próprio registo — 1 query,
    não 1 por família em paralelo."""
    ttl = catalog_cache_ttl()
    cache_key = f"catalog:modelo-auto:{id_modelo}"

    def load():
        row = (
            get_db()
            .table(PRODUCT_MODELS_TABLE)
            .select("tipo_catalogo")
            .eq("id", id_modelo)
            .limit(1)
            .execute()
            .data
            or [None]
        )[0]
        tipo = row.get("tipo_catalogo") if row else None
        if not tipo or tipo not in CATALOG_TYPES:
            raise HTTPException(status_code=404, detail="Modelo não encontrado")
        data = model_detail_for_tipo(tipo, id_modelo)
        if not data:
            raise HTTPException(status_code=404, detail="Modelo não encontrado")
        data["_tipo_catalogo"] = tipo
        data["_storefront_mode"] = CATALOG_TYPES[tipo].get("storefront_mode") or "variantes"
        return data

    try:
        return await asyncio.to_thread(get_or_set, cache_key, float(ttl), load)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Detalhe modelo auto %s: %s", id_modelo, exc)
        raise HTTPException(status_code=500, detail="Erro ao carregar modelo") from exc


@router.get("/{tipo}/modelos-catalogo/{id_categoria}")
async def list_storefront_catalog(
    tipo: str,
    id_categoria: str,
    request: Request,
    filter_tipo: str | None = None,
    limit: int = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
):
    """Lista modelos para a loja (vitrine) — visível apenas, paginada no servidor."""
    _require_tipo(tipo)
    # Rota pública: sem tecto, ?limit= enorme lia a tabela toda e criava uma entrada de cache por valor.
    limit = min(max(limit, 1), DEFAULT_PAGE_LIMIT)
    offset = max(offset, 0)
    query_filters = {
        key[7:]: value
        for key, value in request.query_params.items()
        if key.startswith("filter_") and value
    }
    filter_key = "|".join(f"{k}={v}" for k, v in sorted(query_filters.items()))
    ttl = catalog_cache_ttl()
    cache_key = f"catalog:list:{tipo}:{id_categoria}:{filter_tipo or ''}:{filter_key}:{limit}:{offset}"

    def load():
        return catalogue_for_category(
            tipo,
            id_categoria,
            filters=query_filters or None,
            tipo_filter=filter_tipo,
            limit=limit,
            offset=offset,
        )

    try:
        return await asyncio.to_thread(get_or_set, cache_key, float(ttl), load)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Catálogo %s/%s: %s", tipo, id_categoria, exc)
        raise HTTPException(status_code=500, detail="Erro ao carregar catálogo") from exc


@router.get("/{tipo}/modelo-detalhe/slug/{category_slug}/{model_slug}")
async def get_storefront_model_detail_by_slug(tipo: str, category_slug: str, model_slug: str):
    _require_tipo(tipo)
    ttl = catalog_cache_ttl()
    cache_key = f"catalog:modelo-slug:{tipo}:{category_slug}:{model_slug}"

    def load():
        data = model_detail_for_slugs(tipo, category_slug, model_slug)
        if not data:
            raise HTTPException(status_code=404, detail="Modelo não encontrado")
        return data

    try:
        return await asyncio.to_thread(get_or_set, cache_key, float(ttl), load)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Detalhe modelo slug %s/%s/%s: %s", tipo, category_slug, model_slug, exc)
        raise HTTPException(status_code=500, detail="Erro ao carregar modelo") from exc


@router.get("/{tipo}/modelo-detalhe/{id_modelo}")
async def get_storefront_model_detail(tipo: str, id_modelo: str):
    _require_tipo(tipo)
    ttl = catalog_cache_ttl()
    cache_key = f"catalog:modelo:{tipo}:{id_modelo}"

    def load():
        data = model_detail_for_tipo(tipo, id_modelo)
        if not data:
            raise HTTPException(status_code=404, detail="Modelo não encontrado")
        return data

    try:
        return await asyncio.to_thread(get_or_set, cache_key, float(ttl), load)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Detalhe modelo %s/%s: %s", tipo, id_modelo, exc)
        raise HTTPException(status_code=500, detail="Erro ao carregar modelo") from exc


def _resolve_merged_tipos(tipo_catalogo: str | None) -> list[str] | None:
    """None = sem filtro (todas as famílias). Lista vazia = família inexistente."""
    if not tipo_catalogo:
        return None
    aggregated = aggregated_tipos_for_tipo(tipo_catalogo)
    if aggregated:
        return list(aggregated)
    return [tipo_catalogo] if is_valid_tipo(tipo_catalogo) else []


def _load_merged_page(
    *,
    view_key: str,
    visible_only: bool,
    limit: int,
    offset: int,
    categoria_id: str | None,
    modelo_id: str | None,
    tipos: list[str] | None,
) -> tuple[list[dict], int]:
    physical = PRODUCT_MODELS_TABLE if view_key == "modelos" else PRODUCT_VARIANTS_TABLE
    db = get_db()

    query = db.table(physical).select(admin_merged_select_query(physical), count="exact")
    if visible_only:
        query = query.eq("visibilidade", True)
    if tipos is not None:
        if not tipos:
            return [], 0
        query = query.in_("tipo_catalogo", tipos)
    if categoria_id and view_key == "modelos":
        query = query.eq("id_categoria", categoria_id)
    if categoria_id and view_key == "produtos":
        model_ids = [
            str(r["id"])
            for r in db.table(PRODUCT_MODELS_TABLE).select("id").eq("id_categoria", categoria_id).execute().data or []
        ]
        if not model_ids:
            return [], 0
        query = query.in_("id_modelo", model_ids)
    if modelo_id and view_key == "produtos":
        query = query.eq("id_modelo", modelo_id)

    try:
        res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    except TypeError:
        res = query.order("created_at", ascending=False).range(offset, offset + limit - 1).execute()

    rows = res.data or []
    total = getattr(res, "count", None)
    if total is None:
        total = offset + len(rows)

    from models.catalog_registry import model_table_for_tipo, product_table_for_tipo

    for item in rows:
        tipo = item.get("tipo_catalogo")
        item["_ptable"] = (model_table_for_tipo(tipo) if view_key == "modelos" else product_table_for_tipo(tipo)) or physical
        item["_tipo_catalogo"] = tipo
        item["_familia_label"] = tipo_label(tipo)
        cat_nome = None
        if isinstance(item.get("categories"), dict):
            cat_nome = item["categories"].get("nome")
        elif isinstance(item.get(PRODUCT_MODELS_TABLE), dict):
            emb_cat = item[PRODUCT_MODELS_TABLE].get("categories")
            if isinstance(emb_cat, dict):
                cat_nome = emb_cat.get("nome")
        item["_categoria_label"] = cat_nome or item["_familia_label"]
    return rows, total


@router.get(
    "/admin/merged/{view_key}",
    dependencies=[Depends(admin_must_be_local), Depends(require_catalog_role)],
)
async def admin_merged_list(
    view_key: str,
    visible_only: bool = False,
    limit: int = 80,
    offset: int = 0,
    categoria_id: str | None = None,
    modelo_id: str | None = None,
    tipo_catalogo: str | None = None,
):
    """Lista merged para backoffice (modelos ou produtos) — paginada no servidor."""
    if not is_catalog_view(view_key):
        raise HTTPException(status_code=400, detail="Vista inválida")
    for label, value in (("categoria_id", categoria_id), ("modelo_id", modelo_id)):
        if value:
            try:
                UUID(value)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"{label} inválido") from None
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    tipos = _resolve_merged_tipos(tipo_catalogo)

    cache_key = (
        f"admin:merged:{view_key}:v{int(visible_only)}:c{categoria_id or ''}:"
        f"m{modelo_id or ''}:t{tipo_catalogo or ''}:l{limit}:o{offset}"
    )

    def _load() -> tuple[list[dict], int]:
        return _load_merged_page(
            view_key=view_key,
            visible_only=visible_only,
            limit=limit,
            offset=offset,
            categoria_id=categoria_id,
            modelo_id=modelo_id,
            tipos=tipos,
        )

    rows, total = await asyncio.to_thread(get_or_set, cache_key, float(catalog_cache_ttl()), _load)
    return {"items": rows, "limit": limit, "offset": offset, "count": len(rows), "total_approx": total}
