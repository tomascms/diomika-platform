"""Todo o URL que a loja (e o QR da etiqueta) faz para um modelo tem de abrir a ficha.

A loja faz o URL a partir do nome (`slugifyName`): «Cinto Extensivel» -> /categoria/cintos/cinto-extensivel. O slug
gravado pode ser outro (o do cinto era `extensivel`) e a 2026-11-10 a ficha dava «já não está disponível». A API aceita
os dois, em todas as famílias, para os modelos e para as categorias.
"""
from __future__ import annotations

import pytest
from catalog_db_fake import CAT, use_db  # noqa: F401  (fixture)
from catalog_db_fake import model, variant

from core.cache_warmup import slugify

FAMILIES = sorted({(key, cat["tipo_catalogo"]) for key, cat in CAT.items() if cat["visibilidade"]})


@pytest.mark.parametrize(("category", "tipo"), FAMILIES)
def test_the_name_url_and_the_saved_slug_both_find_the_model(use_db, category, tipo):
    from core.catalog_storefront import _find_model_id_by_slug

    m = model("m-1", "Cinto Extensível", tipo, category, [variant("5606044501319")])
    m["slug"] = "extensivel"  # gravado diferente do nome
    use_db([m, model("m-2", "Outro", tipo, category, [variant("5606044501326")])])
    cat_id = CAT[category]["id"]

    assert _find_model_id_by_slug(cat_id, tipo, slugify(m["nome"])) == "m-1"  # cinto-extensivel
    assert _find_model_id_by_slug(cat_id, tipo, "extensivel") == "m-1"
    assert _find_model_id_by_slug(cat_id, tipo, "nao-existe") is None


def test_a_hidden_model_stays_hidden_by_either_url(use_db):
    from core.catalog_storefront import _find_model_id_by_slug

    m = model("m-1", "Cinto Extensível", "almofada", "almofada", [variant("5606044501319")], visible=False)
    use_db([m])

    assert _find_model_id_by_slug("c-almofada", "almofada", "cinto-extensivel") is None


def test_a_category_is_found_by_its_slug_or_by_its_name(use_db):
    from core.catalog_storefront import _resolve_public_category_id

    use_db([])
    assert _resolve_public_category_id("protetores-colchao") == "c-colchao"  # slug gravado
    assert _resolve_public_category_id("protetor-de-colchao") == "c-colchao"  # nome
    assert _resolve_public_category_id("categoria-oculta") is None  # escondida
