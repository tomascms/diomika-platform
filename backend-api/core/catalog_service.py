"""Operações de catálogo genéricas — dispatch por CATALOG_TYPES."""
from __future__ import annotations

from fastapi import HTTPException

from core.catalog_storefront import (
    catalogue_models_aggregated,
    catalogue_models_for_tipo,
    model_detail_for_tipo_query,
)
from models.catalog_registry import is_valid_storefront_tipo, storefront_filters_for_category_tipo
from models.schemas import aggregated_tipos_for_tipo


def _resolve_storefront_filters(
    tipo: str,
    filters: dict[str, str] | None,
    tipo_filter: str | None,
) -> dict[str, str]:
    active = {k: v for k, v in (filters or {}).items() if v}
    if tipo_filter and not active:
        agg = aggregated_tipos_for_tipo(tipo)
        if agg and tipo_filter in agg:
            active["_tipo_catalogo"] = tipo_filter
        else:
            filter_defs = storefront_filters_for_category_tipo(tipo)
            if filter_defs:
                active[filter_defs[0]["field"]] = tipo_filter
    return active


def catalogue_for_category(
    tipo: str,
    id_categoria: str,
    *,
    filters: dict[str, str] | None = None,
    tipo_filter: str | None = None,
    limit: int = 24,
    offset: int = 0,
) -> list:
    if not is_valid_storefront_tipo(tipo):
        raise HTTPException(status_code=404, detail=f"Tipo de catálogo «{tipo}» desconhecido.")
    active = _resolve_storefront_filters(tipo, filters, tipo_filter)
    if aggregated_tipos_for_tipo(tipo):
        return catalogue_models_aggregated(tipo, id_categoria, filters=active, limit=limit, offset=offset)
    db_filters = {k: v for k, v in active.items() if not k.startswith("_")}
    return catalogue_models_for_tipo(tipo, id_categoria, filters=db_filters, limit=limit, offset=offset)


def model_detail_for_tipo(tipo: str, id_modelo: str) -> dict | None:
    if not is_valid_storefront_tipo(tipo):
        raise HTTPException(status_code=404, detail=f"Tipo de catálogo «{tipo}» desconhecido.")
    if aggregated_tipos_for_tipo(tipo):
        for physical in aggregated_tipos_for_tipo(tipo) or []:
            data = model_detail_for_tipo_query(physical, id_modelo)
            if data:
                data["_tipo_catalogo"] = physical
                data["_category_tipo"] = tipo
                data["_familia_label"] = data.get("_familia_label") or physical
                return data
        return None
    return model_detail_for_tipo_query(tipo, id_modelo)


def model_detail_for_slugs(tipo: str, category_slug: str, model_slug: str) -> dict | None:
    from core.catalog_storefront import model_detail_for_slugs_query

    if not is_valid_storefront_tipo(tipo):
        raise HTTPException(status_code=404, detail=f"Tipo de catálogo «{tipo}» desconhecido.")
    return model_detail_for_slugs_query(tipo, category_slug, model_slug)
