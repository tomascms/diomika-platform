"""Enriquecer linhas de pedido para PDF (EAN → nome modelo/cor)."""
from __future__ import annotations

from core.catalog_storefront import resolve_product_lines_batch


def enrich_order_lines(linhas: list[dict]) -> list[dict]:
    return resolve_product_lines_batch(linhas)
