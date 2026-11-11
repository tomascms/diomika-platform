"""A quantidade mínima é da categoria e é também o passo do pedido (12 → 12, 24, 36…)."""
import pytest

from models.catalog_attributes import CATEGORY_ATTRIBUTE_SCHEMAS
from models.schemas import Categoria
from models.ui_schema import FIELD_LABELS_PT


def _cat(**kw):
    return Categoria(nome="Toalhas", imagem="x.webp", tipo_catalogo="toalha_mesa", **kw)


def test_minimum_is_also_the_step():
    c = _cat(carrinho_min=12, carrinho_step=6)
    assert (c.carrinho_min, c.carrinho_step) == (12, 12)


def test_default_comes_from_the_family():
    c = _cat()
    assert c.carrinho_step == c.carrinho_min


def test_minimum_must_be_positive():
    with pytest.raises(ValueError):
        _cat(carrinho_min=0)


def test_label_and_models_have_no_increment():
    assert FIELD_LABELS_PT["carrinho_min"] == "Quantidade mínima"
    for cfg in CATEGORY_ATTRIBUTE_SCHEMAS.values():
        assert "incremento" not in cfg["model_attributes"]
