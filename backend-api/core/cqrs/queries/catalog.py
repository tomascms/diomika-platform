"""Queries CQRS — leituras públicas de categorias + resolução de linhas."""
from __future__ import annotations

from dataclasses import dataclass

from core.database import get_db


@dataclass
class ListCategoriesQuery:
    visible_only: bool = True


def list_categories(q: ListCategoriesQuery):
    from core.public_api import PUBLIC_CATEGORY_FIELDS, public_category

    db = get_db()
    query = db.table("categories").select(PUBLIC_CATEGORY_FIELDS)
    if q.visible_only:
        query = query.eq("visibilidade", True)
    rows = query.order("nome").execute().data or []
    return [public_category(r) for r in rows]


def resolve_line_display(ean: str, numero_cor: int, altura: str | None = None) -> dict:
    """Resolve EAN + numero_cor (+ altura) para labels no email/PDF."""
    from core.catalog_storefront import resolve_product_line

    return resolve_product_line(ean, numero_cor, altura)
