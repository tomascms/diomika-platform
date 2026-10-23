"""
Registo de tipos de catálogo — lê CATALOG_TYPES de schemas.py e
CATEGORY_ATTRIBUTE_SCHEMAS de catalog_attributes.py.

Esquema unificado: só 3 tabelas físicas para todas as categorias
(product_models, product_variants, product_model_colors), discriminadas por
`tipo_catalogo`. Os nomes de tabela "virtuais" (ex.: "modelos_almofadas",
"almofada") continuam a existir como chaves em TABLE_MAP — compatíveis com as
rotas /admin/crud/{table} já existentes — e resolvem para a tabela física +
filtro via `physical_table_for()` / `tipo_for_table()`.

Não dupliques tipos aqui: edita models/catalog_attributes.py.
"""
from __future__ import annotations

from typing import Type

from pydantic import BaseModel

from models.schemas import (
    CATALOG_TYPES,
    PRODUCT_MODEL_COLORS_TABLE,
    PRODUCT_MODELS_TABLE,
    PRODUCT_VARIANTS_TABLE,
    TIPO_CATALOGO_LABELS,
    aggregated_tipos_for_tipo,
    is_registered_tipo,
)

CATALOGO_TIPOS = CATALOG_TYPES


def is_valid_tipo(tipo: str | None) -> bool:
    return bool(tipo and tipo in CATALOG_TYPES)


def is_valid_storefront_tipo(tipo: str | None) -> bool:
    return is_registered_tipo(tipo)


def tipo_label(tipo: str | None) -> str:
    if not tipo:
        return ""
    if tipo in CATALOG_TYPES:
        return CATALOG_TYPES[tipo].get("label") or TIPO_CATALOGO_LABELS.get(tipo, tipo)
    from models.schemas import CATEGORY_DEFINITIONS

    for definition in CATEGORY_DEFINITIONS.values():
        if definition.get("tipo_catalogo") == tipo:
            return str(definition.get("nome") or tipo)
    return TIPO_CATALOGO_LABELS.get(tipo, tipo)


# --- Nomes de tabela virtuais (1 por tipo_catalogo) <-> tabela física real ---

def _table_entry(table: str | None) -> dict | None:
    if not table:
        return None
    from models.schemas import TABLE_MAP

    return TABLE_MAP.get(table)


def physical_table_for(table: str | None) -> str | None:
    """Tabela física real (product_models/product_variants/product_model_colors)
    para um nome de tabela virtual. Tabelas não-catálogo (categories, infra,
    operações) são já o seu próprio nome físico."""
    entry = _table_entry(table)
    if entry and entry.get("_physical_table"):
        return entry["_physical_table"]
    return table


def tipo_for_table(table: str | None) -> str | None:
    """tipo_catalogo correspondente a um nome de tabela virtual."""
    entry = _table_entry(table)
    if entry:
        return entry.get("_tipo_catalogo")
    return None


def level_for_table(table: str | None) -> str | None:
    """'model' | 'variant' | 'colors' para um nome de tabela virtual de catálogo."""
    entry = _table_entry(table)
    return entry.get("_level") if entry else None


def is_catalog_virtual_table(table: str | None) -> bool:
    return level_for_table(table) is not None


def fold_attributes(table: str | None, body: dict) -> dict:
    """Aceita campos de atributo soltos no nível de topo de um registo (ex.:
    `tipo`, `dimensoes` vindos de um CSV ou de um pedido antigo) e dobra-os em
    `attributes: {...}`, como o esquema unificado espera. Campos que não
    pertencem ao registo de atributos da categoria ficam no nível de topo."""
    from models.catalog_attributes import CATEGORY_ATTRIBUTE_SCHEMAS

    tipo = tipo_for_table(table)
    level = level_for_table(table)
    if not tipo or level not in ("model", "variant"):
        return body
    attr_names = set((CATEGORY_ATTRIBUTE_SCHEMAS.get(tipo) or {}).get(f"{level}_attributes") or {})
    if not attr_names:
        return body
    out = dict(body)
    attrs = dict(out.get("attributes") or {})
    for name in attr_names:
        if name in out and name not in attrs:
            attrs[name] = out.pop(name)
    out["attributes"] = attrs
    return out


def model_table_for_tipo(tipo: str | None) -> str | None:
    if not is_valid_tipo(tipo):
        return None
    from models.catalog_attributes import VIRTUAL_TABLE_NAMES

    return VIRTUAL_TABLE_NAMES[tipo]["model"]


def product_table_for_tipo(tipo: str | None) -> str | None:
    if not is_valid_tipo(tipo):
        return None
    from models.catalog_attributes import VIRTUAL_TABLE_NAMES

    return VIRTUAL_TABLE_NAMES[tipo]["variant"]


def colors_table_for_tipo(tipo: str | None) -> str | None:
    if not is_valid_tipo(tipo):
        return None
    from models.catalog_attributes import VIRTUAL_TABLE_NAMES

    return VIRTUAL_TABLE_NAMES[tipo]["colors"]


def colors_table_for_model_table(model_table: str | None) -> str | None:
    tipo = tipo_for_table(model_table)
    return colors_table_for_tipo(tipo) if tipo else None


def colors_schema_for_tipo(tipo: str | None) -> Type[BaseModel] | None:
    if not is_valid_tipo(tipo):
        return None
    return CATALOG_TYPES[tipo].get("colors_schema")


def model_schema_for_tipo(tipo: str | None) -> Type[BaseModel] | None:
    if not is_valid_tipo(tipo):
        return None
    return CATALOG_TYPES[tipo]["model_schema"]


def product_schema_for_tipo(tipo: str | None) -> Type[BaseModel] | None:
    if not is_valid_tipo(tipo):
        return None
    return CATALOG_TYPES[tipo]["product_schema"]


def all_model_tables() -> list[str]:
    from models.catalog_attributes import VIRTUAL_TABLE_NAMES

    return [v["model"] for v in VIRTUAL_TABLE_NAMES.values()]


def all_product_tables() -> list[str]:
    from models.catalog_attributes import VIRTUAL_TABLE_NAMES

    return [v["variant"] for v in VIRTUAL_TABLE_NAMES.values()]


def all_colors_tables() -> list[str]:
    from models.catalog_attributes import VIRTUAL_TABLE_NAMES

    return [v["colors"] for v in VIRTUAL_TABLE_NAMES.values()]


def all_catalog_tables() -> list[str]:
    return all_model_tables() + all_product_tables() + all_colors_tables()


def is_model_table(table: str | None) -> bool:
    return level_for_table(table) == "model"


def is_product_table(table: str | None) -> bool:
    return level_for_table(table) == "variant"


def is_colors_table(table: str | None) -> bool:
    return level_for_table(table) == "colors"


def product_readonly_on_edit(table: str | None) -> bool:
    tipo = tipo_for_table(table)
    if not tipo:
        return False
    return bool(CATALOG_TYPES[tipo].get("product_readonly_on_edit"))


def apply_barcode_on_save(table: str | None) -> bool:
    tipo = tipo_for_table(table)
    if not tipo:
        return False
    return bool(CATALOG_TYPES[tipo].get("apply_barcode_on_save"))


def storefront_mode_for_tipo(tipo: str | None) -> str:
    if not is_valid_tipo(tipo):
        return "variantes"
    return CATALOG_TYPES[tipo].get("storefront_mode") or "variantes"


def is_assento_tipo(tipo: str | None) -> bool:
    return storefront_mode_for_tipo(tipo) == "assento"


def list_select_query(table: str) -> str:
    """Query Supabase para listas do backoffice/loja — esquema unificado:
    `attributes` (jsonb) já vem dentro de `*`, não há mais colunas por família."""
    physical = physical_table_for(table)
    if physical == PRODUCT_VARIANTS_TABLE:
        return f"*, {PRODUCT_MODELS_TABLE}(nome, attributes, categories(nome))"
    if physical == PRODUCT_MODELS_TABLE:
        return "*, categories(nome)"
    if physical == PRODUCT_MODEL_COLORS_TABLE:
        # !inner: as cores não têm `tipo_catalogo` próprio, por isso a família
        # filtra-se pelo modelo-pai embutido (ver _scoped_list em admin_crud).
        return f"*, {PRODUCT_MODELS_TABLE}!inner(nome, tipo_catalogo)"
    return "*"


def admin_merged_select_query(table: str) -> str:
    """Select leve para listas merged do admin."""
    return admin_list_select_query(table, embed_category=True)


def admin_list_select_query(table: str, *, embed_category: bool = False) -> str:
    """Select leve para listagens do backoffice (sem * nem embeds pesados).
    Esquema unificado: `attributes` substitui as colunas por-família, por isso
    pedir uma coluna inexistente numa categoria deixou de ser possível."""
    if table == "categories":
        return "id, nome, tipo_catalogo, visibilidade, slug, created_at"
    physical = physical_table_for(table)
    if physical == PRODUCT_VARIANTS_TABLE:
        cols = ["id", "ean", "tipo_catalogo", "attributes", "visibilidade", "created_at", "id_modelo"]
        if embed_category:
            return f"{', '.join(cols)}, {PRODUCT_MODELS_TABLE}(nome, categories(nome))"
        return f"{', '.join(cols)}, {PRODUCT_MODELS_TABLE}(nome)"
    if physical == PRODUCT_MODELS_TABLE:
        cols = ["id", "nome", "tipo_catalogo", "attributes", "visibilidade", "created_at", "id_categoria"]
        if embed_category:
            return f"{', '.join(cols)}, categories(nome)"
        return ", ".join(cols)
    if physical == PRODUCT_MODEL_COLORS_TABLE:
        # !inner: ver list_select_query — a família de uma cor vem do modelo-pai.
        return f"id, numero, nome, visibilidade, id_modelo, created_at, {PRODUCT_MODELS_TABLE}!inner(tipo_catalogo)"
    # Tabelas não-catálogo (orçamentos, encomendas, mensagens): `nome` é o que
    # identifica a linha na lista do backoffice — sem ele mostrava o id.
    return "id, nome, visibilidade, created_at"


def relation_options_select_query(table: str) -> str:
    """Mínimo para dropdowns de relação no formulário."""
    if table == "categories":
        return "id, nome, tipo_catalogo"
    physical = physical_table_for(table)
    if physical == PRODUCT_MODELS_TABLE:
        return "id, nome, tipo_catalogo"
    if physical == PRODUCT_VARIANTS_TABLE:
        return "id, ean, id_modelo, tipo_catalogo"
    if physical == PRODUCT_MODEL_COLORS_TABLE:
        return f"id, numero, nome, id_modelo, {PRODUCT_MODELS_TABLE}!inner(tipo_catalogo)"
    return "id, nome"


def aggregated_family_filter(tipo: str | None) -> dict | None:
    tipos = aggregated_tipos_for_tipo(tipo)
    if not tipos:
        return None
    return {
        "field": "_tipo_catalogo",
        "label": "Subcategoria",
        "options": tipos,
        "labels": {t: CATALOG_TYPES[t]["label"] for t in tipos if t in CATALOG_TYPES},
    }


def storefront_filters_for_model_tipo(tipo: str | None) -> list[dict]:
    if not is_valid_tipo(tipo):
        return []
    cfg = CATALOG_TYPES[tipo]
    return list(cfg["storefront_filters"]) if cfg.get("storefront_filters") else []


def storefront_filters_for_category_tipo(tipo: str | None) -> list[dict]:
    agg = aggregated_family_filter(tipo)
    if agg:
        return [agg]
    return storefront_filters_for_model_tipo(tipo)


def catalog_metadata() -> dict:
    """Metadados para API/loja — tipos, tabelas, modos de vitrine."""
    from models.schemas import CATEGORY_DEFINITIONS
    from models.storefront_meta import storefront_context_for_tipo

    tipos = []
    for key, cfg in CATALOG_TYPES.items():
        ctx = storefront_context_for_tipo(key, cfg)
        tipos.append(
            {
                "tipo": key,
                "label": cfg.get("label") or key,
                "model_table": model_table_for_tipo(key),
                "product_table": product_table_for_tipo(key),
                "colors_table": colors_table_for_tipo(key),
                "storefront_mode": ctx["mode"],
                "storefront_filters": storefront_filters_for_model_tipo(key),
                "storefront_picker": ctx["picker"],
                "storefront_specs": ctx["specs"],
                "storefront_badge": ctx["badge"],
                "order_picker_mode": ctx["mode"],
            }
        )

    aggregated = []
    for _slug, definition in CATEGORY_DEFINITIONS.items():
        virtual = definition.get("tipo_catalogo")
        if virtual and aggregated_tipos_for_tipo(virtual):
            fam = aggregated_family_filter(virtual)
            aggregated.append(
                {
                    "tipo": virtual,
                    "label": definition.get("nome") or virtual,
                    "aggregated_tipos": list(definition["aggregated_tipos"]),
                    "storefront_mode": "aggregado",
                    "storefront_filters": [fam] if fam else [],
                }
            )

    return {
        "catalog_types": tipos,
        "aggregated_categories": aggregated,
        "category_definitions": CATEGORY_DEFINITIONS,
    }
