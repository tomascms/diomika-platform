"""Validação do registo de atributos por categoria — substitui as 13 classes
Pydantic por-família que existiam antes do refactor de esquema."""
from __future__ import annotations

import pytest


def test_almofada_model_requires_tipo_composicao_dimensoes():
    from models.catalog_attributes import validate_attributes

    out = validate_attributes(
        "almofada", "model", {"tipo": "decorativa", "composicao": {"algodao": 100}, "dimensoes": ["50x50"]}
    )
    assert out == {"tipo": "decorativa", "composicao": {"algodao": 100}, "dimensoes": ["50x50"]}

    with pytest.raises(ValueError, match="obrigatório"):
        validate_attributes("almofada", "model", {"tipo": "decorativa", "dimensoes": ["50x50"]})


def test_composicao_must_sum_100():
    from models.catalog_attributes import validate_attributes

    with pytest.raises(ValueError, match="100%"):
        validate_attributes(
            "almofada", "model", {"tipo": "decorativa", "composicao": {"algodao": 90}, "dimensoes": ["50x50"]}
        )


def test_dimensoes_must_match_nxn_pattern():
    from models.catalog_attributes import validate_attributes

    with pytest.raises(ValueError, match="comprimento"):
        validate_attributes(
            "almofada", "model", {"tipo": "decorativa", "composicao": {"algodao": 100}, "dimensoes": ["grande"]}
        )


def test_enum_rejects_unknown_value():
    from models.catalog_attributes import validate_attributes

    with pytest.raises(ValueError, match="inválido"):
        validate_attributes(
            "almofada", "model", {"tipo": "gigante", "composicao": {"algodao": 100}, "dimensoes": ["50x50"]}
        )


def test_variant_dimension_single_validated():
    from models.catalog_attributes import validate_attributes

    assert validate_attributes("almofada", "variant", {"dimensoes": "100x200"}) == {"dimensoes": "100x200"}
    with pytest.raises(ValueError):
        validate_attributes("almofada", "variant", {"dimensoes": "invalid"})


def test_oculo_segmento_optional_and_hidden():
    from models.catalog_attributes import attribute_form_fields, validate_attributes

    # segmento tem default None e é "hidden" — não aparece no formulário...
    fields = attribute_form_fields("oculo", "variant")
    assert fields == []
    # ...mas continua validado se vier preenchido.
    out = validate_attributes("oculo", "variant", {})
    assert out == {"segmento": None}
    out = validate_attributes("oculo", "variant", {"segmento": "homem"})
    assert out == {"segmento": "homem"}
    with pytest.raises(ValueError):
        validate_attributes("oculo", "variant", {"segmento": "robot"})


def test_regional_requires_dimensoes_only_for_some_subtipos():
    from models.catalog_attributes import validate_attributes

    # avental/luva/pega não precisam de dimensões
    out = validate_attributes("regional", "model", {"subtipo": "luva", "composicao": {"algodao": 100}})
    assert out["dimensoes"] is None

    # toalha/protetor/pano_cozinha precisam
    with pytest.raises(ValueError, match="dimensões"):
        validate_attributes("regional", "model", {"subtipo": "toalha", "composicao": {"algodao": 100}})

    out = validate_attributes(
        "regional", "model", {"subtipo": "toalha", "composicao": {"algodao": 100}, "dimensoes": ["100x200"]}
    )
    assert out["dimensoes"] == ["100x200"]


def test_guarda_chuva_has_no_extra_attributes():
    from models.catalog_attributes import validate_attributes

    assert validate_attributes("guarda_chuva", "model", {}) == {}
    assert validate_attributes("guarda_chuva", "variant", {}) == {}


def test_unknown_tipo_rejected():
    from models.catalog_attributes import validate_attributes

    with pytest.raises(ValueError, match="não está registado"):
        validate_attributes("mantas", "model", {})


def test_all_twelve_categories_have_consistent_virtual_table_names():
    from models.catalog_attributes import CATEGORY_ATTRIBUTE_SCHEMAS, VIRTUAL_TABLE_NAMES

    assert set(CATEGORY_ATTRIBUTE_SCHEMAS) == set(VIRTUAL_TABLE_NAMES)
    for tipo, names in VIRTUAL_TABLE_NAMES.items():
        assert names["model"].startswith("modelos_") or names["model"] == "modelos_almofadas"
        assert names["colors"].startswith("modelo_") and names["colors"].endswith("_cores")
