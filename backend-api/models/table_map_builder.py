"""Gera TABLE_MAP — nomes de tabela são virtuais (um por tipo_catalogo,
compatíveis com os nomes de antes do refactor); resolvem para as 3 tabelas
físicas partilhadas via `_physical_table` + filtro `_tipo_catalogo`.
Não editar tipos aqui: edita models/catalog_attributes.py."""
from __future__ import annotations

from typing import Any

from models.catalog_attributes import CATEGORY_ATTRIBUTE_SCHEMAS, VIRTUAL_TABLE_NAMES, attribute_form_fields


def build_unified_catalog_table_map(*, model_schema, variant_schema, colors_schema) -> dict[str, dict]:
    """Entradas de modelo/variante/cores — uma por tipo_catalogo, nomes
    virtuais iguais aos de antes (ex.: "modelos_almofadas", "almofada")."""
    out: dict[str, dict] = {}
    for tipo, names in VIRTUAL_TABLE_NAMES.items():
        cfg = CATEGORY_ATTRIBUTE_SCHEMAS.get(tipo) or {}
        label = cfg.get("label") or tipo.title()
        mt, pt, ct = names["model"], names["variant"], names["colors"]

        model_filters: list[dict] = [
            {"field": "id_categoria", "relation": "categories", "label": "Categoria"},
        ]
        for f in attribute_form_fields(tipo, "model"):
            if f["widget"] == "enum":
                model_filters.append(
                    {"field": f"attributes.{f['name']}", "label": f["label"], "type": "enum", "options": f["enum_options"] or [], "labels": f["enum_labels"] or {}}
                )

        out[mt] = {
            "schema": model_schema,
            "label": f"Modelos {label}",
            "icon": "layers",
            "ui_sidebar": False,
            "list_label_fields": ["nome"],
            "ui_embed_colors": True,
            "ui_filters": model_filters,
            "ui_catalog_tipo": tipo,
            "ui_attribute_fields": attribute_form_fields(tipo, "model"),
            "ui_colors_table": ct,
            "_physical_table": "product_models",
            "_tipo_catalogo": tipo,
            "_level": "model",
        }

        mode = cfg.get("storefront_mode") or "variantes"
        out[pt] = {
            "schema": variant_schema,
            "label": f"Produtos {label}",
            "icon": "shopping_cart",
            "ui_sidebar": False,
            "ui_list_formatter": "assento" if mode == "assento" else "produto",
            "ui_filters": [
                {"field": "id_modelo", "relation": mt, "label": "Modelo"},
                {"field": "ean", "type": "search", "label": "EAN"},
            ],
            "ui_catalog_tipo": tipo,
            "ui_attribute_fields": attribute_form_fields(tipo, "variant"),
            "_physical_table": "product_variants",
            "_tipo_catalogo": tipo,
            "_level": "variant",
        }

        out[ct] = {
            "schema": colors_schema,
            "label": f"Cores — {label}",
            "icon": "palette",
            "ui_sidebar": False,
            "list_label_fields": ["numero", "nome"],
            "ui_catalog_tipo": tipo,
            "_physical_table": "product_model_colors",
            "_tipo_catalogo": tipo,
            "_level": "colors",
        }
    return out


def build_operations_table_map(
    *,
    categoria_schema,
    pedido_schema,
    encomenda_schema,
    contact_schema,
    infra_schemas: dict[str, Any],
) -> dict[str, dict]:
    """Tabelas fixas: categorias, operações, infra."""
    out = {
        "categories": {
            "schema": categoria_schema,
            "label": "Categorias",
            "icon": "folder",
            "list_label_fields": ["nome", "tipo_catalogo"],
            "ui_no_filters": True,
        },
        "pedidos_orcamento": {
            "schema": pedido_schema,
            "label": "Orçamentos",
            "icon": "receipt",
            "ui_mode": "order_view",
            "ui_no_create": True,
            "ui_no_filters": True,
            "ui_list_formatter": "order_cliente",
        },
        "encomendas_internas": {
            "schema": encomenda_schema,
            "label": "Encomendas",
            "icon": "clipboard",
            "ui_mode": "order_create",
            "ui_no_filters": True,
            "ui_list_formatter": "order_cliente",
            "list_label_fields": ["referencia_cliente"],
        },
        "contact_messages": {
            "schema": contact_schema,
            "label": "Mensagens",
            "icon": "mail",
            "ui_mode": "conversation",
            "ui_no_create": True,
            "ui_no_filters": True,
            "ui_list_formatter": "contact",
        },
    }
    for table_name, schema in infra_schemas.items():
        out[table_name] = {
            "schema": schema,
            "label": table_name.replace("_", " ").title(),
            "icon": "database",
            "ui_sidebar": False,
            "ui_hidden_infra": True,
        }
    return out
