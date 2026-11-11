"""Pesquisa no catálogo (auditoria BR-02, FE-06, RP-07).

«almofada» é o nome de uma categoria com 2 modelos e dava «Sem resultados»; «colchão» e «colchao» davam resultados
diferentes; cores, medidas, materiais e EAN não se encontravam. Cada teste pesquisa num catálogo pequeno, com as formas
dos dados de produção (modelos com `attributes`, cores numa tabela à parte, variantes com EAN), e diz o que tem de sair.
"""
from __future__ import annotations

import pytest
from catalog_db_fake import use_db  # noqa: F401  (fixture)
from catalog_db_fake import model, variant
from fastapi.testclient import TestClient

from core import cache, catalog_search

MODELS = [
    model("m-agate", "Agate", "almofada", "almofada", [variant("5606044199011", dimensoes="35x55"), variant("5606044191237", dimensoes="45x45")], tipo="decorativa", composicao={"Veludo": 100}),
    model("m-foglia", "Foglia", "almofada", "almofada", [variant("5606044301018", dimensoes="45x45"), variant("5606044301025", dimensoes="60x60")], ("Azul Ciano", "Azul Marinho", "Bege", "Vermelho"), tipo="decorativa", composicao={"Poliester": 100}),
    model("m-termica", "Almofada Térmica", "almofada", "calor", [variant("5606044400011", dimensoes="30x40")], ("Cinza",), tipo="dormir", composicao={"Algodão": 100}),
    model("m-liso", "Liso", "assento", "assento", [variant("5606044500010", altura="32mm"), variant("5606044500027", altura="45mm")], material_forro="Poliéster", material_enchimento="Poliuretano"),
    model("m-napa", "Napa", "assento", "assento", [variant("5606044500034", altura="32mm")], material_forro="PVC", material_enchimento="Poliuretano"),
    model("m-colchao", "Protetor Colchão Malha", "protetor_colchao", "colchao", [variant("5606044600017", dimensoes="90x200")], composicao={"Poliéster": 100}),
    model("m-toalha", "Toalha PVC", "toalha_mesa", "mesa", [variant("5606044700014", dimensoes="140x180")], ("Branco", "Natal"), tipo_produto="toalha", composicao={"PVC": 100}),
    model("m-oculos", "Adulto", "oculo", "oculos", [variant("5606044800011")], tipo_oculo="sol"),
    # Não se mostram: sem EAN (os guarda-chuvas de produção), escondido, sem cor visível, variante escondida, categoria escondida.
    model("m-guarda", "Guarda-Chuva Clássico", "guarda_chuva", "guarda", [variant("")]),
    model("m-escondido", "Almofada Escondida", "almofada", "almofada", [variant("5606044900018", dimensoes="50x50")], visible=False),
    model("m-sem-cor", "Almofada Sem Cor", "almofada", "almofada", [variant("5606044900025", dimensoes="50x50")], colours=()),
    model("m-var-escondida", "Almofada Sem Variante", "almofada", "almofada", [{**variant("5606044900032", dimensoes="50x50"), "visibilidade": False}]),
    model("m-cat-escondida", "Almofada De Categoria Oculta", "almofada", "oculta", [variant("5606044900049", dimensoes="50x50")]),
]


@pytest.fixture
def catalogue(use_db):
    """O catálogo acima como base de dados; a cache de pesquisa limpa antes e depois."""
    return use_db(MODELS)


def names(query, **kwargs):
    return [hit["model"]["nome"] for hit in catalog_search.search_storefront(query, **kwargs)]


# --- Palavras ---------------------------------------------------------------------------------------------------


def test_tokens_ignore_accents_case_plural_and_write_measures_the_same_way():
    assert catalog_search.tokens("Óculos de Sol") == ["oculo", "de", "sol"]
    assert catalog_search.tokens("Guarda-Chuvas") == ["guarda", "chuva"]
    assert catalog_search.tokens("45 x 45") == ["45x45"]
    assert catalog_search.tokens("45×45") == ["45x45"]
    assert catalog_search.tokens("32 mm") == ["32mm"]
    assert catalog_search.tokens("5606044199011") == ["5606044199011"]
    assert catalog_search.query_tokens("toalhas de mesa") == ["toalha", "mesa"]
    assert catalog_search.query_tokens("de") == ["de"]  # só palavras vazias: usam-se mesmo assim


def test_a_pathological_query_is_cut_down(catalogue):
    words = catalog_search.query_tokens("palavra " * 50 + "x" * 500)
    assert len(words) == 8 and all(len(word) <= 40 for word in words)
    assert names("almofada " * 100) == names("almofada")  # não rebenta nem demora


def test_a_typo_is_one_edit_away():
    within = catalog_search._within
    assert within("almofda", "almofada", 1)  # falta uma letra
    assert within("amlofada", "almofada", 1)  # duas letras trocadas
    assert within("almofadda", "almofada", 1)  # uma a mais
    assert within("almofeda", "almofada", 1)  # uma errada
    assert not within("almofdaa", "almofado", 1)
    assert not within("cadeira", "almofada", 2)


# --- O que se encontra ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("query", ["almofada", "Almofada", "ALMOFADA", "almofadas", " almofada "])
def test_a_category_name_finds_its_models_whatever_the_case_and_the_plural(catalogue, query):
    assert set(names(query)) == {"Agate", "Foglia", "Almofada Térmica"}


@pytest.mark.parametrize("query", ["almofda", "amlofada", "almofadda", "Almofdas"])
def test_a_typo_in_the_category_name_still_finds_it(catalogue, query):
    assert set(names(query)) == {"Agate", "Foglia", "Almofada Térmica"}


def test_short_words_do_not_forgive_typos(catalogue):
    """«lisa» não é «liso»: com 4 letras uma troca já é outra palavra."""
    assert names("lisa") == []
    assert names("nada que exista") == []
    assert names("") == [] and names("   ") == []


def test_a_wrong_digit_is_not_a_typo(catalogue):
    """Uma gralha perdoa-se numa palavra; 45x46 ou um EAN com um dígito trocado são outro artigo."""
    assert names("45x46") == []
    assert names("5606044199012") == []


def test_a_name_beats_a_category(catalogue):
    """Quem escreve «almofada» e há um modelo chamado «Almofada Térmica» quer esse primeiro."""
    assert names("almofada")[0] == "Almofada Térmica"


@pytest.mark.parametrize("query", ["azul", "Azul", "azul marinho", "ciano", "vermelho"])
def test_a_colour_name_finds_the_model(catalogue, query):
    assert names(query) == ["Foglia"]


@pytest.mark.parametrize("query", ["45x45", "45 x 45", "45×45", "45X45"])
def test_a_measure_finds_the_models_sold_in_it_however_it_is_written(catalogue, query):
    assert set(names(query)) == {"Agate", "Foglia"}


def test_one_side_of_a_measure_and_heights_also_work(catalogue):
    assert set(names("60")) == {"Foglia"}
    assert set(names("32mm")) == {"Liso", "Napa"}
    assert set(names("32 mm")) == {"Liso", "Napa"}
    assert names("45mm") == ["Liso"]
    assert names("90x200") == ["Protetor Colchão Malha"]


def test_an_ean_finds_its_model_first_a_piece_of_it_finds_the_family(catalogue):
    assert names("5606044199011") == ["Agate"]
    assert names("5606044301025") == ["Foglia"]
    assert set(names("56060443010")) == {"Foglia"}
    # Menos de 4 dígitos não é um pedaço de EAN: «199» não encontra o Agate (nem tudo o que tem esses dígitos).
    assert names("199") == []


def test_composition_and_materials_ignore_accents(catalogue):
    assert names("veludo") == ["Agate"]
    assert names("poliester") == ["Foglia", "Liso", "Protetor Colchão Malha"]
    assert names("Poliéster") == names("poliester")
    # «PVC» é o nome de uma toalha e o forro de um assento: o nome vale mais do que o material.
    assert names("pvc") == ["Toalha PVC", "Napa"]
    assert names("poliuretano") == ["Liso", "Napa"]


def test_the_kind_of_product_finds_it(catalogue):
    assert set(names("decorativa")) == {"Agate", "Foglia"}
    assert names("dormir") == ["Almofada Térmica"]
    assert names("óculos de sol") == ["Adulto"]


def test_accented_and_plain_spellings_give_the_same_results(catalogue):
    assert names("colchão") == names("colchao") == ["Protetor Colchão Malha"]
    assert names("protetores") == ["Protetor Colchão Malha"]
    assert names("oculos") == names("óculos") == ["Adulto"]


def test_several_words_must_all_appear_each_in_any_field(catalogue):
    assert names("almofada azul") == ["Foglia"]
    assert set(names("Almofada decorativa 45x45")) == {"Agate", "Foglia"}
    assert names("toalhas de mesa") == ["Toalha PVC"]
    assert names("almofada assento") == []


def test_only_what_the_store_shows_is_found(catalogue):
    found = set(names("almofada"))
    assert not found & {"Almofada Escondida", "Almofada Sem Cor", "Almofada Sem Variante", "Almofada De Categoria Oculta"}
    # Os guarda-chuvas estão visíveis na base de dados mas sem EAN: a loja não os mostra e a pesquisa também não.
    assert names("guarda-chuva") == []
    assert names("5606044900018") == []


def test_the_limit_and_the_shape_of_each_result(catalogue):
    assert len(catalog_search.search_storefront("almofada", limit=2)) == 2

    first = catalog_search.search_storefront("foglia")[0]
    assert set(first) == {"model", "category", "cover_path", "_tipo_catalogo"}
    assert first["_tipo_catalogo"] == "almofada"
    assert first["category"] == {"id": "c-almofada", "nome": "Almofada", "slug": "almofada", "tipo_catalogo": "almofada"}
    assert first["cover_path"] == "m-foglia-1.png"
    detail = first["model"]
    assert detail["nome"] == "Foglia" and detail["categories"]["nome"] == "Almofada"
    assert [c["nome"] for c in detail["modelo_cores"]][:2] == ["Azul Ciano", "Azul Marinho"]
    assert [v["ean"] for v in detail["product_variants"]] == ["5606044301018", "5606044301025"]


# --- O índice e a cache -----------------------------------------------------------------------------------------


def test_the_index_is_built_once_and_a_catalogue_write_refreshes_it(catalogue, monkeypatch):
    builds = []
    real = catalog_search.build_index
    monkeypatch.setattr(catalog_search, "build_index", lambda: builds.append(1) or real())

    names("almofada")
    names("azul")
    assert len(builds) == 1  # as pesquisas seguintes usam o índice em cache

    catalogue.models.append(model("m-novo", "Almofada Nova", "almofada", "almofada", [variant("5606044950012", dimensoes="40x40")], ("Rosa",), tipo="decorativa"))
    catalogue.colours.extend(catalogue.models[-1]["_colours"])
    # Ainda não se vê: a cache só muda quando alguém grava no backoffice.
    assert "Almofada Nova" not in names("almofada")

    cache.invalidate_catalog_change(table_name="modelos_almofadas", record={"id": "m-novo", "id_categoria": "c-almofada"}, record_id="m-novo")

    assert "Almofada Nova" in names("almofada")
    assert names("rosa") == ["Almofada Nova"]
    assert len(builds) == 2


def test_the_route_answers_the_same_way_and_ignores_one_letter(catalogue):
    import main

    client = TestClient(main.app, base_url="http://localhost")
    headers = {"User-Agent": "Mozilla/5.0 test"}

    hits = client.get("/catalogo/search", params={"q": "almofda"}, headers=headers)
    assert hits.status_code == 200
    assert {hit["model"]["nome"] for hit in hits.json()} == {"Agate", "Foglia", "Almofada Térmica"}
    assert client.get("/catalogo/search", params={"q": "a"}, headers=headers).json() == []
