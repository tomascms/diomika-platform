"""Queries de listagem do catálogo."""
from __future__ import annotations


def test_list_select_query_product_joins_category_via_model():
    """Esquema unificado: 1 tabela física para todas as variantes — `attributes`
    (jsonb) substitui as colunas por-categoria que existiam antes (dimensoes,
    alturas, ...)."""
    from models.catalog_registry import list_select_query

    assert list_select_query("almofada") == "*, product_models(nome, attributes, categories(nome))"
    assert list_select_query("assento") == "*, product_models(nome, attributes, categories(nome))"


def test_list_select_query_model_joins_category_directly():
    from models.catalog_registry import list_select_query

    assert list_select_query("modelos_almofadas") == "*, categories(nome)"


def test_storefront_tipo_includes_aggregated():
    from models.catalog_registry import is_valid_storefront_tipo, storefront_filters_for_category_tipo

    assert is_valid_storefront_tipo("material_cozinha")
    assert not is_valid_storefront_tipo("unknown")
    filters = storefront_filters_for_category_tipo("material_cozinha")
    assert filters[0]["field"] == "_tipo_catalogo"
    assert "avental" in filters[0]["options"]


def test_catalog_types_registered():
    from models.schemas import CATALOG_TYPES

    expected = {
        "almofada",
        "assento",
        "guarda_chuva",
        "oculo",
        "toalha_mesa",
        "avental",
        "luva",
        "pega",
        "pano_cozinha",
        "protetor_colchao",
        "passadeira",
        "regional",
    }
    assert set(CATALOG_TYPES) == expected
    assert CATALOG_TYPES["almofada"]["model_discriminator_field"] == "dimensoes"
    # Esquema unificado: as 3 tabelas físicas são as mesmas para todas as famílias.
    for cfg in CATALOG_TYPES.values():
        assert cfg["model_table"] == "product_models"
        assert cfg["product_table"] == "product_variants"
        assert cfg["colors_table"] == "product_model_colors"


def test_virtual_table_resolution_round_trips():
    """Nomes de tabela virtuais (ex.: 'almofada', 'modelos_almofadas') continuam
    a existir para as rotas /admin/crud/{table} — resolvem para a tabela física
    + tipo_catalogo correctos."""
    from models.catalog_registry import (
        is_colors_table,
        is_model_table,
        is_product_table,
        level_for_table,
        physical_table_for,
        tipo_for_table,
    )

    assert physical_table_for("almofada") == "product_variants"
    assert physical_table_for("modelos_almofadas") == "product_models"
    assert physical_table_for("modelo_assento_cores") == "product_model_colors"
    assert physical_table_for("categories") == "categories"  # não-catálogo: identidade

    assert tipo_for_table("almofada") == "almofada"
    assert tipo_for_table("modelos_assentos") == "assento"
    assert tipo_for_table("categories") is None

    assert level_for_table("almofada") == "variant"
    assert level_for_table("modelos_almofadas") == "model"
    assert level_for_table("modelo_almofada_cores") == "colors"

    assert is_product_table("almofada") and not is_model_table("almofada")
    assert is_model_table("modelos_almofadas") and not is_product_table("modelos_almofadas")
    assert is_colors_table("modelo_almofada_cores")


def test_product_readonly_and_barcode_flags_by_virtual_table():
    from models.catalog_registry import apply_barcode_on_save, product_readonly_on_edit

    assert product_readonly_on_edit("almofada") is True
    assert apply_barcode_on_save("almofada") is True
    assert apply_barcode_on_save("categories") is False
