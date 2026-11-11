"""Informação de produto que o comprador B2B pede antes de encomendar (auditoria RP-08).

Cuidados de lavagem, embalagem (un. por caixa), gramagem, origem, certificações e prazo: campos opcionais, iguais em
todas as famílias, que o cliente preenche no backoffice (ficha do cliente, Parte D, itens 14 e 15). A loja mostra os que
estiverem preenchidos. Vivem em `attributes` (jsonb): não há migração.
"""
from __future__ import annotations

import pytest

INFO_FIELDS = ["cuidados", "embalagem", "gramagem", "origem", "certificacao", "prazo"]
ALMOFADA = {"tipo": "decorativa", "composicao": {"algodao": 100}, "dimensoes": ["50x50"]}


def test_every_family_has_the_six_optional_fields():
    from models.catalog_attributes import CATEGORY_ATTRIBUTE_SCHEMAS

    assert len(CATEGORY_ATTRIBUTE_SCHEMAS) >= 12
    for tipo, cfg in CATEGORY_ATTRIBUTE_SCHEMAS.items():
        model_attributes = cfg["model_attributes"]
        for name in INFO_FIELDS:
            assert name in model_attributes, f"{tipo} sem {name}"
            assert model_attributes[name]["required"] is False, f"{tipo}.{name} não é opcional"


def test_the_fields_are_saved_and_cleaned():
    from models.catalog_attributes import validate_attributes

    out = validate_attributes(
        "almofada",
        "model",
        {
            **ALMOFADA,
            "cuidados": "  Lavar a 30 °C, não usar lixívia  ",
            "embalagem": "12",
            "gramagem": 180,
            "origem": "Portugal",
            "certificacao": "OEKO-TEX Standard 100",
            "prazo": "5 a 10 dias úteis",
        },
    )

    assert out["cuidados"] == "Lavar a 30 °C, não usar lixívia"
    assert out["embalagem"] == 12 and isinstance(out["embalagem"], int)
    assert out["gramagem"] == 180
    assert (out["origem"], out["certificacao"], out["prazo"]) == ("Portugal", "OEKO-TEX Standard 100", "5 a 10 dias úteis")


def test_old_models_stay_valid_and_unchanged():
    """Um modelo sem estes campos continua válido e o `attributes` não ganha seis «null»."""
    from models.catalog_attributes import validate_attributes

    assert validate_attributes("almofada", "model", ALMOFADA) == ALMOFADA
    assert validate_attributes("guarda_chuva", "model", {}) == {}
    # Preenchidos e depois apagados no backoffice (vazio): também saem.
    assert validate_attributes("almofada", "model", {**ALMOFADA, "cuidados": "", "embalagem": None, "origem": "   "}) == ALMOFADA


@pytest.mark.parametrize("field", ["embalagem", "gramagem"])
@pytest.mark.parametrize("bad", ["abc", "12.5", 0, -3, True])
def test_whole_numbers_only(field, bad):
    from models.catalog_attributes import validate_attributes

    with pytest.raises(ValueError, match=r"número inteiro|maior do que zero"):
        validate_attributes("almofada", "model", {**ALMOFADA, field: bad})


def test_the_store_lists_the_filled_specifications_after_the_family_ones():
    """A loja recebe estas especificações no `_storefront.specs` e mostra as que têm valor."""
    from models.storefront_meta import storefront_badge_for_model, storefront_picker_for_type, storefront_specs_for_model
    from models.catalog_attributes import CATEGORY_ATTRIBUTE_SCHEMAS

    cfg = {**CATEGORY_ATTRIBUTE_SCHEMAS["almofada"], "_tipo": "almofada"}
    specs = storefront_specs_for_model("almofada", storefront_picker_for_type(cfg), storefront_badge_for_model("almofada"))

    assert [s["field"] for s in specs] == ["composicao", "dimensoes", *INFO_FIELDS]
    labels = {s["field"]: s["label"] for s in specs}
    assert labels["cuidados"] == "Cuidados de lavagem"
    assert labels["embalagem"] == "Embalagem (un. por caixa)"
    assert labels["gramagem"] == "Gramagem (g/m²)"
    assert labels["origem"] == "País de origem"
    assert labels["certificacao"] == "Certificações"
    assert labels["prazo"] == "Prazo de entrega"


def test_the_backoffice_form_shows_them_as_optional_text_fields():
    from models.catalog_attributes import attribute_form_fields

    fields = {f["name"]: f for f in attribute_form_fields("toalha_mesa", "model")}

    for name in INFO_FIELDS:
        assert fields[name]["required"] is False
        assert fields[name]["widget"] == "text"
        assert fields[name]["placeholder"]
    # Os campos que já existiam continuam à frente.
    names = list(fields)
    assert names.index("composicao") < names.index("cuidados")
