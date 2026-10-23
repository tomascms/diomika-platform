"""A API da loja continua a expor os atributos específicos da categoria no
nível de topo do modelo/produto (ex.: `product.dimensoes`, `model.tipo_oculo`),
mesmo agora que vivem dentro de `attributes` (jsonb) na base de dados — o
frontend-web (storefront) não foi — e não precisa de ser — reescrito para
saber disso."""
from __future__ import annotations

from core.catalog_storefront import _finalize_model_products, _flatten_attrs


def test_flatten_attrs_copies_attribute_keys_to_top_level():
    row = {"id": "m1", "nome": "Almofada X", "attributes": {"tipo": "decorativa", "dimensoes": ["50x50"]}}
    out = _flatten_attrs(row)
    assert out["tipo"] == "decorativa"
    assert out["dimensoes"] == ["50x50"]
    assert out["attributes"] == {"tipo": "decorativa", "dimensoes": ["50x50"]}  # continua disponível também


def test_flatten_attrs_real_columns_win_over_same_named_attribute():
    row = {"id": "m1", "nome": "x", "attributes": {"nome": "deveria perder"}}
    out = _flatten_attrs(row)
    assert out["nome"] == "x"


def test_flatten_attrs_no_attributes_is_noop():
    row = {"id": "m1", "nome": "x"}
    assert _flatten_attrs(row) == row


def test_finalize_model_products_flattens_each_variant_attributes():
    row = {
        "id": "m1",
        "modelo_cores": [{"numero": 1, "imagem": "x.jpg", "visibilidade": True}],
        "almofada": [
            {"id": "p1", "ean": "5600000000013", "visibilidade": True, "attributes": {"dimensoes": "100x200"}},
        ],
    }
    ok = _finalize_model_products(row, "almofada", "variantes")
    assert ok is True
    assert row["almofada"][0]["dimensoes"] == "100x200"


def test_finalize_model_products_assento_sorts_by_flattened_altura():
    row = {
        "id": "m1",
        "modelo_cores": [{"numero": 1, "imagem": "x.jpg", "visibilidade": True}],
        "assento": [
            {"id": "p1", "ean": "5600000000013", "visibilidade": True, "attributes": {"altura": "45mm"}},
            {"id": "p2", "ean": "5600000000037", "visibilidade": True, "attributes": {"altura": "32mm"}},
        ],
    }
    ok = _finalize_model_products(row, "assento", "assento")
    assert ok is True
    assert [p["altura"] for p in row["assento"]] == ["32mm", "45mm"]
