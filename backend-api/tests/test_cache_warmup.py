"""O aquecimento usa as mesmas chaves que os URLs da loja (slugify igual ao do frontend)."""
from __future__ import annotations

from core.cache_warmup import _category_slug, _model_slug, slugify


def test_slugify_matches_frontend():
    # Valores obtidos com slugifyName de frontend-web/src/lib/catalogRoutes.js
    cases = {
        "Cafeteira": "cafeteira",
        "Toalhas de Mesa": "toalhas-de-mesa",
        "Óculos": "oculos",
        "Protetor de Colchão": "protetor-de-colchao",
        "  Guarda-Chuva ": "guarda-chuva",
        "Agaté 2!": "agate-2",
    }
    for raw, expected in cases.items():
        assert slugify(raw) == expected


def test_slug_rules_match_frontend():
    uuid = "6f1c2d3e-4a5b-4c6d-8e7f-0123456789ab"
    assert _category_slug({"slug": "almofada", "nome": "X"}) == "almofada"
    assert _category_slug({"slug": uuid, "nome": "Toalhas de Mesa"}) == "toalhas-de-mesa"
    assert _model_slug({"nome": "Foglia", "slug": "outro"}) == "foglia"
    assert _model_slug({"nome": "", "slug": uuid}) == ""
