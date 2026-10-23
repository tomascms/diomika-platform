"""Validation logic for CRUD operations (model, product, EAN, etc)."""
from __future__ import annotations

import json

from core.database import get_db
from models.catalog_registry import (
    CATALOG_TYPES,
    all_colors_tables,
    all_model_tables,
    all_product_tables,
    tipo_for_table,
)
from models.schemas import PRODUCT_MODELS_TABLE, aggregated_tipos_for_tipo

from .admin_crud_helpers import _attr, _db_table


def _tipo_for_model_id(model_id: str | None) -> str:
    """Get catalog family type for a model."""
    if not model_id:
        raise ValueError("Modelo em falta.")
    row = (
        get_db()
        .table(PRODUCT_MODELS_TABLE)
        .select("tipo_catalogo")
        .eq("id", str(model_id))
        .limit(1)
        .execute()
        .data
        or [None]
    )[0]
    if not row:
        raise ValueError("Modelo não encontrado.")
    return row["tipo_catalogo"]


def _model_attribute_values(model_id: str, field: str) -> list[str]:
    """Get list of available attribute values (e.g., dimensions) defined on model."""
    row = (
        get_db()
        .table(PRODUCT_MODELS_TABLE)
        .select("attributes")
        .eq("id", model_id)
        .limit(1)
        .execute()
        .data
        or [None]
    )[0]
    if not row:
        raise ValueError("Modelo não encontrado.")
    values = (row.get("attributes") or {}).get(field) or []
    if isinstance(values, str):
        try:
            values = json.loads(values)
        except json.JSONDecodeError:
            values = [values]
    return [str(a).strip() for a in values if a and str(a).strip()]


def _validate_model_discriminator(table_name: str, payload: dict, record_id: str | None = None) -> None:
    """Validate model discriminator field (altura/dimensoes) for variants."""
    tipo = tipo_for_table(table_name)
    if not tipo:
        return
    cfg = CATALOG_TYPES.get(tipo) or {}
    model_field = cfg.get("model_discriminator_field")
    if not model_field:
        return

    product_field = "altura" if tipo == "assento" else model_field
    value = str(_attr(payload, product_field) or "").strip()
    if not value:
        raise ValueError(f"Selecione {product_field.replace('_', ' ')} desta variante.")

    id_modelo = payload.get("id_modelo")
    if not id_modelo:
        return

    allowed = _model_attribute_values(str(id_modelo), model_field)
    if value not in allowed:
        raise ValueError(f"«{value}» não está definido no modelo.")

    q = (
        _db_table(table_name)
        .select("id")
        .eq("id_modelo", str(id_modelo))
        .eq(f"attributes->>{product_field}", value)
    )
    if record_id:
        q = q.neq("id", record_id)
    if q.limit(1).execute().data or []:
        raise ValueError(f"Já existe variante «{value}» neste modelo.")




def _validate_oculo(payload: dict, record_id: str | None = None) -> None:
    """Validate óculos (glasses) by type and segment.

    Special case: leitura glasses have no discriminator, just one product per model.
    """
    id_modelo = payload.get("id_modelo")
    if not id_modelo:
        return
    model = (
        _db_table("modelos_oculos")
        .select("attributes")
        .eq("id", str(id_modelo))
        .limit(1)
        .execute()
        .data or [None]
    )[0]
    if not model:
        raise ValueError("Modelo de óculos não encontrado.")

    tipo_oculo = (model.get("attributes") or {}).get("tipo_oculo")
    if tipo_oculo == "leitura":
        if _attr(payload, "segmento"):
            raise ValueError("Óculos de leitura não têm segmento — use produto sortido.")
        q = _db_table("oculo").select("id").eq("id_modelo", str(id_modelo))
        if record_id:
            q = q.neq("id", record_id)
        if q.limit(1).execute().data or []:
            raise ValueError("Este modelo de leitura já tem produto sortido.")
        return
    _validate_model_discriminator("oculo", payload, record_id)


def _validate_regional_product(payload: dict, record_id: str | None = None) -> None:
    """Validate regional product by subtype and dimensions.

    Only some subtypes require a discriminator (pano_cozinha, toalha, protetor).
    """
    id_modelo = payload.get("id_modelo")
    if not id_modelo:
        return
    model = (
        _db_table("modelos_regionais")
        .select("attributes")
        .eq("id", str(id_modelo))
        .limit(1)
        .execute()
        .data or [None]
    )[0]
    if not model:
        raise ValueError("Modelo regional não encontrado.")

    attrs = model.get("attributes") or {}
    subtipo = attrs.get("subtipo")
    needs_dim = subtipo in ("pano_cozinha", "toalha", "protetor")
    dim = str(_attr(payload, "dimensoes") or "").strip()

    if needs_dim:
        if not dim:
            raise ValueError("Selecione dimensão desta variante.")
        allowed = _model_attribute_values(str(id_modelo), "dimensoes")
        if dim not in allowed:
            raise ValueError(f"Dimensão «{dim}» não está definida no modelo.")
        q = _db_table("regional").select("id").eq("id_modelo", str(id_modelo)).eq("attributes->>dimensoes", dim)
        if record_id:
            q = q.neq("id", record_id)
        if q.limit(1).execute().data or []:
            raise ValueError(f"Já existe variante «{dim}» neste modelo.")
    elif dim:
        raise ValueError("Este subtipo não usa dimensão no produto.")


def _product_validation_table(table_name: str) -> bool:
    """Check if table requires product validation."""
    return table_name in all_product_tables()


def _validate_unico_single_product(table_name: str, payload: dict, record_id: str | None = None) -> None:
    """Validate 'unico' mode: one product per model."""
    tipo = tipo_for_table(table_name)
    cfg = CATALOG_TYPES.get(tipo or "") or {}
    if (cfg.get("storefront_mode") or "") != "unico":
        return
    if cfg.get("model_discriminator_field"):
        return
    id_modelo = payload.get("id_modelo")
    if not id_modelo:
        return
    q = _db_table(table_name).select("id").eq("id_modelo", str(id_modelo))
    if record_id:
        q = q.neq("id", record_id)
    if q.limit(1).execute().data or []:
        raise ValueError("Este modelo já tem um produto (modo único — uma referência por modelo).")


def _assert_model_category_tipo(table_name: str, payload: dict) -> None:
    """Ensure model/color/product stays in correct category family."""
    tipo = tipo_for_table(table_name)
    if not tipo:
        return
    db = get_db()
    id_categoria = payload.get("id_categoria")
    id_modelo = payload.get("id_modelo")

    if table_name in all_model_tables():
        if not id_categoria:
            return
        cat = (
            db.table("categories")
            .select("id,nome,tipo_catalogo")
            .eq("id", str(id_categoria))
            .limit(1)
            .execute()
            .data
            or [None]
        )[0]
        if not cat:
            raise ValueError("Categoria não encontrada.")
        cat_tipo = str(cat.get("tipo_catalogo") or "").strip()
        aggregated = aggregated_tipos_for_tipo(cat_tipo) or []
        allowed = set(aggregated) if aggregated else ({cat_tipo} if cat_tipo else {tipo})
        if tipo not in allowed:
            raise ValueError(f"A categoria «{cat.get('nome') or cat_tipo}» não aceita modelos do tipo «{tipo}».")
        return

    if table_name in all_product_tables() or table_name in all_colors_tables():
        if not id_modelo:
            return
        model = (
            db.table(PRODUCT_MODELS_TABLE)
            .select("id,id_categoria,tipo_catalogo")
            .eq("id", str(id_modelo))
            .limit(1)
            .execute()
            .data
            or [None]
        )[0]
        if not model:
            raise ValueError("Modelo não encontrado.")
        if model.get("tipo_catalogo") != tipo:
            raise ValueError("O modelo escolhido não pertence a esta família de produto.")


def _validate_ean_checksum(ean: str | None) -> None:
    """Valida checksum EAN-13 se presente."""
    from utils.ean_validator import get_ean_error_message

    ean_str = str(ean or "").strip()
    if not ean_str:
        return  # EAN é opcional

    error = get_ean_error_message(ean_str)
    if error:
        raise ValueError(f"EAN inválido: {error}")


def _validate_product_payload(table_name: str, payload: dict, record_id: str | None = None) -> None:
    """Run all product-related validations."""
    # Valida EAN checksum se o campo existir
    if "ean" in payload:
        _validate_ean_checksum(payload.get("ean"))

    if table_name == "oculo":
        _validate_oculo(payload, record_id)
    elif table_name == "regional":
        _validate_regional_product(payload, record_id)
    elif _product_validation_table(table_name):
        _validate_model_discriminator(table_name, payload, record_id)
    _validate_unico_single_product(table_name, payload, record_id)


def _assert_model_publishable(table_name: str, record_id: str) -> None:
    """Ensure model can be published: has ≥1 color (image) and ≥1 product (EAN)."""
    if table_name not in all_model_tables():
        return
    db = get_db()
    colors = (
        db.table("product_model_colors")
        .select("id,imagem")
        .eq("id_modelo", record_id)
        .limit(20)
        .execute()
        .data
        or []
    )
    if not any(str(c.get("imagem") or "").strip() for c in colors):
        raise ValueError("Adicione pelo menos uma cor com imagem antes de publicar na loja.")
    products = (
        db.table("product_variants")
        .select("id,ean")
        .eq("id_modelo", record_id)
        .limit(50)
        .execute()
        .data
        or []
    )
    if not any(str(p.get("ean") or "").strip() for p in products):
        raise ValueError("Adicione pelo menos um produto com EAN antes de publicar na loja.")
