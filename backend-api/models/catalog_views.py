"""Vistas unificadas do backoffice — modelos/produtos por categoria."""
from __future__ import annotations

from models.catalog_registry import (
    is_valid_tipo,
    model_table_for_tipo,
    product_table_for_tipo,
    tipo_label,
)
from models.schemas import TABLE_MAP, is_registered_tipo

CATALOG_VIEWS = {
    "modelos": {
        "label": "Modelos",
        "icon": "layers",
        "ui_view": "modelos",
        "ui_filters_base": [
            {"field": "nome", "type": "search", "label": "Nome"},
        ],
    },
    "produtos": {
        "label": "Produtos",
        "icon": "shopping_cart",
        "ui_view": "produtos",
        "ui_filters_base": [
            {"field": "ean", "type": "search", "label": "EAN"},
        ],
    },
}


def is_catalog_view(table_key: str) -> bool:
    return table_key in CATALOG_VIEWS


def physical_table(view_key: str, category_tipo: str | None) -> str | None:
    if view_key == "modelos":
        return model_table_for_tipo(category_tipo)
    if view_key == "produtos":
        return product_table_for_tipo(category_tipo)
    return view_key


def view_config(view_key: str, category_tipo: str | None) -> dict | None:
    """Config efectiva para lista/form (schema da tabela física + filtros da vista)."""
    if view_key not in CATALOG_VIEWS:
        return TABLE_MAP[view_key]

    base = CATALOG_VIEWS[view_key]

    if not category_tipo:
        return {
            "label": base["label"],
            "ui_view": view_key,
            "ui_filters": list(base.get("ui_filters_base") or []),
            "ui_catalog_merged_list": True,
        }

    physical = physical_table(view_key, category_tipo)
    if not physical:
        return None

    cfg = dict(TABLE_MAP[physical])
    cfg["ui_filters"] = list(base.get("ui_filters_base") or [])
    cfg["label"] = base["label"]
    cfg["ui_view"] = view_key
    cfg["ui_physical_table"] = physical
    cfg["ui_category_tipo"] = category_tipo
    cfg["ui_schema_class_name"] = TABLE_MAP[physical]["schema"].__name__
    return cfg


def sidebar_entries() -> dict:
    """Sidebar: categorias + modelos + produtos + operações."""
    out = {"categories": TABLE_MAP["categories"]}
    out.update(CATALOG_VIEWS)
    for key in ("pedidos_orcamento", "encomendas_internas", "contact_messages"):
        out[key] = TABLE_MAP[key]
    return out


def category_tipo_label(tipo: str | None) -> str:
    return tipo_label(tipo)


def category_requires_tipo(category_meta: dict | None) -> bool:
    if not category_meta:
        return True
    return not is_registered_tipo(category_meta.get("tipo_catalogo"))
