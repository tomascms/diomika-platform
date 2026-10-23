"""Uma família nova precisa só de uma entrada em CATEGORY_ATTRIBUTE_SCHEMAS."""
from __future__ import annotations


def test_every_family_has_table_names():
    from models import catalog_attributes as ca

    assert set(ca.VIRTUAL_TABLE_NAMES) >= set(ca.CATEGORY_ATTRIBUTE_SCHEMAS)


def test_default_names_for_new_family():
    from models.catalog_attributes import default_table_names

    assert default_table_names("manta") == {
        "model": "modelos_manta",
        "variant": "manta",
        "colors": "modelo_manta_cores",
    }


def test_new_family_end_to_end_metadata():
    """Simula a entrada nova sem a gravar: o registo resolve tabelas e formulário."""
    from models import catalog_attributes as ca
    from models import catalog_registry as r
    from models import schemas

    ca.CATEGORY_ATTRIBUTE_SCHEMAS["manta"] = {"label": "Mantas", "storefront_mode": "unico", "model_attributes": {}, "variant_attributes": {}}
    ca.VIRTUAL_TABLE_NAMES["manta"] = ca.default_table_names("manta")
    try:
        schemas._register_catalog_types()
        schemas._rebuild_table_map()
        assert r.model_table_for_tipo("manta") == "modelos_manta"
        assert r.physical_table_for("modelos_manta") == "product_models"
        assert r.tipo_for_table("manta") == "manta"
    finally:
        del ca.CATEGORY_ATTRIBUTE_SCHEMAS["manta"]
        del ca.VIRTUAL_TABLE_NAMES["manta"]
        schemas._register_catalog_types()
        schemas._rebuild_table_map()
