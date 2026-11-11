"""O incremento escolhido no modelo é o passo e o mínimo do pedido; sem ele vale o da categoria."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from core.validators import order_lines
from models.catalog_attributes import CATEGORY_ATTRIBUTE_SCHEMAS, quantity_rules, validate_attributes
from models.storefront_meta import storefront_specs_for_model

CAT = {"carrinho_step": 6, "carrinho_min": 6}


def test_rules_prefer_the_model_increment():
    assert quantity_rules(CAT, {"incremento": 12}) == (12, 12)
    assert quantity_rules(CAT, {}) == (6, 6)
    assert quantity_rules({"carrinho_step": 12, "carrinho_min": 6}) == (12, 12)
    assert quantity_rules(None) == (6, 6)


@pytest.mark.parametrize("tipo", sorted(CATEGORY_ATTRIBUTE_SCHEMAS))
def test_every_family_can_set_it_and_the_store_does_not_list_it(tipo):
    assert "incremento" in CATEGORY_ATTRIBUTE_SCHEMAS[tipo]["model_attributes"]
    assert "incremento" not in {s["field"] for s in storefront_specs_for_model(tipo)}


def test_it_must_be_a_positive_integer():
    with pytest.raises(ValueError):
        validate_attributes("cinto", "model", {"incremento": 0})
    assert validate_attributes("cinto", "model", {"incremento": "12"})["incremento"] == 12
    assert "incremento" not in validate_attributes("cinto", "model", {"incremento": ""})


def _lines(monkeypatch, attrs, qty):
    row = {"ean": "1", "id_modelo": "m", "tipo_catalogo": "cinto", "categories": CAT, "model_attributes": attrs}
    monkeypatch.setattr(order_lines, "_load_products_by_ean", lambda eans: ({"1": row}, {"1": "cinto"}))
    monkeypatch.setattr(order_lines, "_valid_model_colors", lambda ids: {("m", 1)})
    order_lines.validate_order_lines([SimpleNamespace(ean="1", quantidade=qty, numero_cor=1, altura=None)])


def test_orders_follow_the_model_increment(monkeypatch):
    _lines(monkeypatch, {"incremento": 12}, 24)
    with pytest.raises(HTTPException):
        _lines(monkeypatch, {"incremento": 12}, 18)
    _lines(monkeypatch, {}, 18)
