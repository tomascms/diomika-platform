"""Pesquisa unificada no catálogo público."""
from __future__ import annotations

import logging

from core.catalog_storefront import models_detail_map_for_tipo
from core.database import get_db
from core.visibility import is_visible
from models.schemas import PRODUCT_MODELS_TABLE
from utils.postgrest_filter import or_literal

logger = logging.getLogger("diomika-api")


def _model_cover_path(model: dict) -> str:
    cores = [c for c in (model.get("modelo_cores") or []) if is_visible(c)]
    cores.sort(key=lambda c: c.get("numero", 0))
    return str((cores[0] or {}).get("imagem") or "")


def _search_models_by_name(q: str, *, limit: int) -> list[dict]:
    """1 query à tabela única de modelos — antes disparava 1 query por família
    de catálogo em paralelo (12 round-trips para o mesmo resultado)."""
    needle = q.strip()
    if len(needle) < 2:
        return []

    try:
        res = (
            get_db()
            .table(PRODUCT_MODELS_TABLE)
            .select("id, nome, slug, tipo_catalogo, visibilidade, id_categoria, categories(id, nome, slug, tipo_catalogo)")
            .eq("visibilidade", True)
            .or_(f"nome.ilike.{or_literal(f'%{needle}%')},slug.ilike.{or_literal(f'%{needle}%')}")
            .limit(max(limit * 2, 16))
            .execute()
        )
    except Exception as exc:
        logger.debug("Search %s: %s", PRODUCT_MODELS_TABLE, exc)
        return []

    ids_by_tipo: dict[str, list[str]] = {}
    categories_by_id: dict[str, dict] = {}
    for row in res.data or []:
        cat = row.get("categories") or {}
        if isinstance(cat, list) and cat:
            cat = cat[0]
        if not isinstance(cat, dict) or not cat.get("id"):
            continue
        tipo = row.get("tipo_catalogo")
        rid = str(row.get("id") or "")
        if not tipo or not rid:
            continue
        ids_by_tipo.setdefault(tipo, []).append(rid)
        categories_by_id[rid] = cat

    out: list[dict] = []
    for tipo, ids in ids_by_tipo.items():
        details = models_detail_map_for_tipo(tipo, ids)
        for mid, detail in details.items():
            out.append(
                {
                    "model": detail,
                    "category": categories_by_id.get(mid, {}),
                    "cover_path": _model_cover_path(detail),
                    "_tipo_catalogo": tipo,
                }
            )

    out.sort(key=lambda r: str((r.get("model") or {}).get("nome") or ""))
    return out[:limit]


def _search_by_ean(q: str, *, limit: int) -> list[dict]:
    needle = q.strip()
    if len(needle) < 3:
        return []
    db = get_db()
    try:
        res = (
            db.table("catalog_ean_lookup")
            .select("tipo, id_modelo, ean, product_visivel, model_visivel")
            .ilike("ean", f"%{needle}%")
            .limit(limit)
            .execute()
        )
    except Exception:
        return []

    out: list[dict] = []
    seen: set[str] = set()
    hits: list[tuple[str, str]] = []
    for row in res.data or []:
        if not row.get("product_visivel") or not row.get("model_visivel"):
            continue
        tipo = str(row.get("tipo") or "")
        mid = str(row.get("id_modelo") or "")
        key = f"{tipo}:{mid}"
        if not mid or key in seen:
            continue
        seen.add(key)
        hits.append((tipo, mid))

    by_tipo: dict[str, list[str]] = {}
    for tipo, mid in hits:
        by_tipo.setdefault(tipo, []).append(mid)
    details: dict[str, dict] = {}
    for tipo, ids in by_tipo.items():
        details.update({f"{tipo}:{k}": v for k, v in models_detail_map_for_tipo(tipo, ids).items()})

    for tipo, mid in hits:
        detail = details.get(f"{tipo}:{mid}")
        if not detail:
            continue
        cat = detail.get("categories") or {}
        out.append(
            {
                "model": detail,
                "category": cat,
                "cover_path": _model_cover_path(detail),
                "_tipo_catalogo": tipo,
            }
        )
    return out


def search_storefront(q: str, *, limit: int = 40) -> list[dict]:
    limit = min(max(limit, 1), 80)
    q = (q or "").strip()
    if not q:
        return []

    if q.isdigit() or any(c.isdigit() for c in q):
        ean_hits = _search_by_ean(q, limit=limit)
        if ean_hits:
            return ean_hits

    name_hits = _search_models_by_name(q, limit=limit)
    if name_hits:
        return name_hits

    return _search_by_ean(q, limit=limit)
