"""Publishing and visibility operations for catalog records.

Cada operação é uma só chamada `rpc` = uma só transacção na BD (db/migrations/2026-11-02_catalogue_functions.sql):
antes eram 1 SELECT + 3 UPDATE soltos, e uma falha a meio deixava pais e filhos com visibilidades diferentes (API-08).
"""
from __future__ import annotations

from core.database import get_db
from models.catalog_registry import all_model_tables


def set_visibility_atomic(kind: str, record_id: str, visible: bool) -> int:
    """kind = «category» ou «model». Devolve quantas linhas do próprio registo mudaram (0 = não existe)."""
    res = (
        get_db()
        .rpc("set_catalog_visibility", {"p_kind": kind, "p_id": str(record_id), "p_visible": bool(visible)})
        .execute()
    )
    return int(res.data or 0)


def _publish_catalog_children(table_name: str, record_id: str, *, tipo: str | None = None) -> None:
    """Make child colors and products visible when model is published."""
    if table_name in all_model_tables():
        set_visibility_atomic("model", record_id, True)


def _hide_catalog_children(table_name: str, record_id: str, *, tipo: str | None = None) -> None:
    """Hide child colors and products when model is hidden."""
    if table_name in all_model_tables():
        set_visibility_atomic("model", record_id, False)


def _cascade_category_visibility(category_id: str, vis: bool) -> None:
    """Categoria, modelos, cores e variantes mudam juntos."""
    set_visibility_atomic("category", category_id, vis)
