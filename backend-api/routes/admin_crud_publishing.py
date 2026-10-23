"""Publishing and visibility operations for catalog records."""
from __future__ import annotations

from core.database import get_db
from models.catalog_registry import all_model_tables
from models.schemas import PRODUCT_MODELS_TABLE

from .admin_crud_helpers import _db_table


def _publish_catalog_children(table_name: str, record_id: str, *, tipo: str | None = None) -> None:
    """Make child colors and products visible when model is published."""
    if table_name not in all_model_tables():
        return
    db = get_db()
    db.table("product_variants").update({"visibilidade": True}).eq("id_modelo", record_id).execute()
    db.table("product_model_colors").update({"visibilidade": True}).eq("id_modelo", record_id).execute()


def _hide_catalog_children(table_name: str, record_id: str, *, tipo: str | None = None) -> None:
    """Hide child colors and products when model is hidden."""
    if table_name not in all_model_tables():
        return
    db = get_db()
    db.table("product_variants").update({"visibilidade": False}).eq("id_modelo", record_id).execute()
    db.table("product_model_colors").update({"visibilidade": False}).eq("id_modelo", record_id).execute()


def _cascade_category_visibility(category_id: str, vis: bool) -> None:
    """Cascade visibility change to child models (and their colors/products).

    Executes 3 queries total (1 select + 2 batch updates) instead of 1 + N*3.
    """
    db = get_db()
    models = (
        db.table(PRODUCT_MODELS_TABLE)
        .select("id")
        .eq("id_categoria", str(category_id))
        .execute()
        .data
        or []
    )
    model_ids = [str(row.get("id") or "") for row in models if row.get("id")]
    if not model_ids:
        return

    db.table(PRODUCT_MODELS_TABLE).update({"visibilidade": vis}).in_("id", model_ids).execute()
    db.table("product_variants").update({"visibilidade": vis}).in_("id_modelo", model_ids).execute()
    db.table("product_model_colors").update({"visibilidade": vis}).in_("id_modelo", model_ids).execute()
