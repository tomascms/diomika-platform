"""Queries CQRS — leituras públicas de categorias + resolução de linhas."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from core.database import get_db

logger = logging.getLogger("diomika-api")


@dataclass
class ListCategoriesQuery:
    visible_only: bool = True


def list_categories(q: ListCategoriesQuery):
    from core.catalog_storefront import showable_model_counts
    from core.public_api import PUBLIC_CATEGORY_FIELDS, public_category

    db = get_db()
    query = db.table("categories").select(PUBLIC_CATEGORY_FIELDS)
    if q.visible_only:
        query = query.eq("visibilidade", True)
    rows = query.order("nome").execute().data or []
    categories = [public_category(r) for r in rows]
    # `modelos_visiveis`: a loja esconde as categorias com 0 (FE-05, RP-03). É um extra: se a contagem falhar a lista
    # sai como antes, sem ela, e a loja mostra todas as categorias em vez de ficar sem nenhuma.
    try:
        counts = showable_model_counts()
    except Exception:
        logger.warning("Contagem de modelos por categoria falhou; a lista sai sem ela", exc_info=True)
        return categories
    return [{**category, "modelos_visiveis": counts.get(str(category.get("id")), 0)} for category in categories]


def resolve_line_display(ean: str, numero_cor: int, altura: str | None = None) -> dict:
    """Resolve EAN + numero_cor (+ altura) para labels no email/PDF."""
    from core.catalog_storefront import resolve_product_line

    return resolve_product_line(ean, numero_cor, altura)
