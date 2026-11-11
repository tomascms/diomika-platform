"""Categorias vazias (auditoria FE-05, RP-03, SEO-04).

A API de categorias diz quantos modelos a loja mostra em cada uma (`modelos_visiveis`), para a loja esconder as que
não têm nenhum. «Mostra» é a mesma regra da lista da categoria e do pré-render: modelo visível, com uma cor visível
e com uma variante visível que tenha EAN. Um modelo visível sem EAN (os guarda-chuvas) não conta.
"""
from __future__ import annotations

import pytest

from core import cache

CAT_ALMOFADA = "4bba6298-b2d8-4d80-9303-49118f2bb29c"
CAT_GUARDA_CHUVA = "d4037b3a-64aa-4a02-86f3-ecce8b4cc6e7"
CAT_REGIONAL = "6eb42cc1-f652-4ab0-bde1-c028db32c8ef"
EAN = "5606044199011"


class _Query:
    def __init__(self, db, name):
        self.db, self.name, self.in_values = db, name, None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def in_(self, _column, values):
        self.in_values = list(values)
        self.db.in_calls.append((self.name, len(self.in_values)))
        return self

    def execute(self):
        if self.db.fail_on == self.name:
            raise RuntimeError("base de dados em baixo")
        rows = self.db.rows.get(self.name, [])
        if self.in_values is not None:
            rows = [r for r in rows if r["id_modelo"] in self.in_values]
        return type("Result", (), {"data": rows})()


class _Db:
    def __init__(self, rows, fail_on=None):
        self.rows, self.fail_on, self.in_calls = rows, fail_on, []

    def table(self, name):
        return _Query(self, name)


def _model(model_id, category, *, visible=True, variants=None):
    return {
        "id": model_id,
        "id_categoria": category,
        "visibilidade": visible,
        "product_variants": [{"ean": EAN, "visibilidade": True}] if variants is None else variants,
    }


def _color(model_id, *, visible=True):
    return {"id_modelo": model_id, "numero": 1, "nome": "Sortido", "imagem": "x.png", "visibilidade": visible}


def _use(monkeypatch, db):
    from core import catalog_storefront

    monkeypatch.setattr(catalog_storefront, "get_db", lambda: db)
    monkeypatch.setattr("core.cqrs.queries.catalog.get_db", lambda: db)


def test_only_showable_models_are_counted_per_category(monkeypatch):
    from core.catalog_storefront import showable_model_counts

    db = _Db(
        {
            "product_models": [
                _model("m1", CAT_ALMOFADA),
                _model("m2", CAT_ALMOFADA),
                # Os três guarda-chuvas de produção: visíveis, sem nenhum EAN.
                _model("g1", CAT_GUARDA_CHUVA, variants=[]),
                _model("g2", CAT_GUARDA_CHUVA, variants=[{"ean": "", "visibilidade": True}]),
                _model("g3", CAT_GUARDA_CHUVA, variants=[{"ean": None, "visibilidade": True}]),
                # Sem cor visível, e com a única variante escondida.
                _model("c1", CAT_REGIONAL),
                _model("v1", CAT_REGIONAL, variants=[{"ean": EAN, "visibilidade": False}]),
            ],
            "product_model_colors": [
                _color("m1"),
                _color("m2"),
                _color("g1"),
                _color("g2"),
                _color("g3"),
                _color("c1", visible=False),
                _color("v1"),
            ],
        }
    )
    _use(monkeypatch, db)

    assert showable_model_counts() == {CAT_ALMOFADA: 2}


def test_colours_are_read_in_small_batches(monkeypatch):
    """O catálogo todo numa só lista `in.(…)` rebentava o limite do URL quando o catálogo crescesse."""
    from core.catalog_storefront import showable_model_counts

    ids = [f"00000000-0000-4000-8000-{n:012d}" for n in range(250)]
    db = _Db(
        {
            "product_models": [_model(i, CAT_ALMOFADA) for i in ids],
            "product_model_colors": [_color(i) for i in ids],
        }
    )
    _use(monkeypatch, db)

    assert showable_model_counts() == {CAT_ALMOFADA: 250}
    assert db.in_calls and max(size for _name, size in db.in_calls) <= 80


def test_categories_list_carries_the_count_and_empty_ones_say_zero(monkeypatch):
    from core.cqrs.queries.catalog import ListCategoriesQuery, list_categories

    base = {"imagem": "i.png", "tipo_catalogo": "almofada", "carrinho_step": 12, "carrinho_min": 12}
    db = _Db(
        {
            "categories": [
                {"id": CAT_ALMOFADA, "nome": "Almofada", "slug": "almofada", **base},
                {"id": CAT_GUARDA_CHUVA, "nome": "Guarda-Chuva", "slug": "guarda-chuvas", **base},
            ],
            "product_models": [_model("m1", CAT_ALMOFADA), _model("g1", CAT_GUARDA_CHUVA, variants=[])],
            "product_model_colors": [_color("m1"), _color("g1")],
        }
    )
    _use(monkeypatch, db)

    out = {c["slug"]: c for c in list_categories(ListCategoriesQuery())}

    assert out["almofada"]["modelos_visiveis"] == 1
    assert out["guarda-chuvas"]["modelos_visiveis"] == 0
    # Os campos de sempre continuam lá, e só eles mais a contagem.
    assert set(out["almofada"]) == {"id", "nome", "slug", "imagem", "tipo_catalogo", "carrinho_step", "carrinho_min", "modelos_visiveis"}


def test_a_failing_count_never_takes_the_category_list_down(monkeypatch):
    """A contagem é um extra: se falhar, a loja recebe as categorias sem ela e mostra-as todas, como antes."""
    from core.cqrs.queries.catalog import ListCategoriesQuery, list_categories

    db = _Db(
        {"categories": [{"id": CAT_ALMOFADA, "nome": "Almofada", "slug": "almofada", "imagem": "i.png", "tipo_catalogo": "almofada", "carrinho_step": 12, "carrinho_min": 12}]},
        fail_on="product_models",
    )
    _use(monkeypatch, db)

    (only,) = list_categories(ListCategoriesQuery())

    assert only["slug"] == "almofada"
    assert "modelos_visiveis" not in only


@pytest.mark.parametrize("table", ["modelos_almofadas", "almofada", "modelo_almofada_cores"])
def test_publishing_or_hiding_a_model_refreshes_the_cached_category_list(monkeypatch, table):
    """`categories:all` vive 1 h na cache; sem isto uma categoria publicada ficava «vazia» até ao fim da hora."""
    monkeypatch.setattr(cache, "get_redis", lambda: None)
    monkeypatch.setattr(cache, "_rewarm_details_later", lambda: None)
    # As variantes e as cores procuram a categoria do modelo na BD: aqui responde esta.
    monkeypatch.setattr("core.database.get_db", lambda: _Db({"product_models": [_model("m1", CAT_ALMOFADA)]}))
    cache._memory_set("categories:all", [{"id": CAT_ALMOFADA, "modelos_visiveis": 0}], 3600)
    assert cache._memory_get("categories:all") is not None

    cache.invalidate_catalog_change(
        table_name=table,
        record={"id_categoria": CAT_ALMOFADA, "id_modelo": "m1", "id": "m1"},
        record_id="m1",
    )

    assert cache._memory_get("categories:all") is None
