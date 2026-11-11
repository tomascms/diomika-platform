"""Uma base de dados de catálogo de mentira, em memória, para os testes da pesquisa e da ficha do modelo.

Responde ao que o código pergunta ao PostgREST (`select`, `eq`, `in_`, `range`…, ignorando o que não muda o resultado) com
linhas do formato das de produção: modelos com `attributes`, cores numa tabela à parte e variantes com EAN.
Ficheiro sem testes: o pytest só recolhe `test_*.py`.
"""
from __future__ import annotations

import pytest

CAT = {
    "almofada": {"id": "c-almofada", "nome": "Almofada", "slug": "almofada", "tipo_catalogo": "almofada", "visibilidade": True},
    "assento": {"id": "c-assento", "nome": "Assento", "slug": "assento", "tipo_catalogo": "assento", "visibilidade": True},
    "colchao": {"id": "c-colchao", "nome": "Protetor de Colchão", "slug": "protetores-colchao", "tipo_catalogo": "protetor_colchao", "visibilidade": True},
    "mesa": {"id": "c-mesa", "nome": "Toalhas de Mesa", "slug": "toalhas-mesa", "tipo_catalogo": "toalha_mesa", "visibilidade": True},
    "oculos": {"id": "c-oculos", "nome": "Óculos", "slug": "oculos", "tipo_catalogo": "oculo", "visibilidade": True},
    "guarda": {"id": "c-guarda", "nome": "Guarda-Chuva", "slug": "guarda-chuvas", "tipo_catalogo": "guarda_chuva", "visibilidade": True},
    "calor": {"id": "c-calor", "nome": "Aquecimento", "slug": "aquecimento", "tipo_catalogo": "almofada", "visibilidade": True},
    "oculta": {"id": "c-oculta", "nome": "Categoria Oculta", "slug": "oculta", "tipo_catalogo": "almofada", "visibilidade": False},
}


def variant(ean, **attributes):
    return {"id": f"v-{ean}", "ean": ean, "visibilidade": True, "attributes": attributes}


def model(model_id, nome, family, category, variants, colours=("Sortido",), *, visible=True, **attributes):
    """`family`: o tipo_catalogo (uma coluna); `attributes`: o jsonb da família, que pode ter o seu próprio `tipo`."""
    return {
        "id": model_id,
        "nome": nome,
        "slug": nome.lower().replace(" ", "-"),
        "tipo_catalogo": family,
        "id_categoria": CAT[category]["id"],
        "visibilidade": visible,
        "attributes": attributes,
        "categories": CAT[category],
        "product_variants": variants,
        "_colours": [
            {"id_modelo": model_id, "numero": n, "nome": name, "imagem": f"{model_id}-{n}.png", "visibilidade": True}
            for n, name in enumerate(colours, 1)
        ],
    }


class FakeQuery:
    def __init__(self, db, name):
        self.db, self.name, self.filters = db, name, []

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column, value):
        self.filters.append(lambda row: row.get(column) == value)
        return self

    def in_(self, column, values):
        self.filters.append(lambda row: row.get(column) in set(values))
        return self

    def range(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        source = {"product_models": self.db.models, "categories": list(CAT.values())}.get(self.name, self.db.colours)
        rows = [dict(row) for row in source if all(check(row) for check in self.filters)]
        for row in rows:
            row.pop("_colours", None)
        return type("Result", (), {"data": rows})()


class FakeDb:
    def __init__(self, models):
        self.models = models
        self.colours = [colour for m in models for colour in m["_colours"]]

    def table(self, name):
        return FakeQuery(self, name)


@pytest.fixture
def use_db(monkeypatch):
    """`use_db(models)` põe a base de dados de mentira no sítio da verdadeira, nos módulos do catálogo."""
    from core import cache, catalog_search, catalog_storefront

    def install(models):
        db = FakeDb(list(models))
        for module in (catalog_search, catalog_storefront):
            monkeypatch.setattr(module, "get_db", lambda: db)
        monkeypatch.setattr(cache, "get_redis", lambda: None)
        cache.invalidate_prefix("catalog:search")
        return db

    yield install
    from core import cache

    cache.invalidate_prefix("catalog:search")
