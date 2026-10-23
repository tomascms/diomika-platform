"""Regressões encontradas numa revisão ao refactor do catálogo unificado.

Todas passavam silenciosamente antes: o conjunto de testes não tocava nestes
caminhos, por isso os defeitos só apareceriam no backoffice do cliente.
"""
from __future__ import annotations


class _FakeQuery:
    """Registo das chamadas .eq() que o builder do PostgREST receberia."""

    def __init__(self):
        self.filters: list[tuple[str, str]] = []

    def eq(self, column, value):
        self.filters.append((column, value))
        return self


def test_scoped_does_not_filter_colors_by_tipo_catalogo():
    """product_model_colors não tem coluna `tipo_catalogo`: filtrá-la dava
    erro 400 do PostgREST em todas as operações de cores do backoffice."""
    from routes.admin_crud import _scoped

    q = _FakeQuery()
    _scoped(q, "modelo_almofada_cores")
    assert q.filters == []


def test_scoped_filters_model_and_variant_by_tipo_catalogo():
    from routes.admin_crud import _scoped

    for table, tipo in (("modelos_almofadas", "almofada"), ("almofada", "almofada")):
        q = _FakeQuery()
        _scoped(q, table)
        assert q.filters == [("tipo_catalogo", tipo)]


def test_scoped_list_filters_colors_through_parent_model():
    """Na listagem a família ainda tem de ser respeitada — senão a lista de
    cores de uma família mostrava as cores de todas, que agora partilham
    a mesma tabela física."""
    from routes.admin_crud import _scoped

    q = _FakeQuery()
    _scoped(q, "modelo_toalha_mesa_cores", use_join=True)
    assert q.filters == [("product_models.tipo_catalogo", "toalha_mesa")]


def test_colors_select_queries_embed_parent_model_as_inner_join():
    """O filtro pelo embed só exclui linhas se o embed for !inner."""
    from models.catalog_registry import (
        admin_list_select_query,
        list_select_query,
        relation_options_select_query,
    )

    for query in (
        list_select_query("modelo_almofada_cores"),
        admin_list_select_query("modelo_almofada_cores"),
        relation_options_select_query("modelo_almofada_cores"),
    ):
        assert "product_models!inner" in query
        assert "tipo_catalogo" in query


def test_admin_list_keeps_nome_for_non_catalog_tables():
    """Sem `nome` as listas de orçamentos/encomendas mostravam o id."""
    from models.catalog_registry import admin_list_select_query

    assert "nome" in admin_list_select_query("pedidos_orcamento")


def test_variant_model_relation_points_at_routable_virtual_table():
    """`product_models` é o nome físico e não é chave do TABLE_MAP, por isso
    /admin/crud/product_models/options dava 404 e o dropdown "Modelo" do
    formulário de variantes ficava sempre vazio."""
    from models.schemas import TABLE_MAP
    from models.ui_schema import get_form_fields

    cfg = TABLE_MAP["almofada"]
    fields = {f["name"]: f for f in get_form_fields(cfg["schema"], cfg, "almofada")}
    relation = fields["id_modelo"]["relation"]
    assert relation == "modelos_almofadas"
    assert relation in TABLE_MAP


def test_category_family_dropdown_has_options():
    """`categories.tipo_catalogo` é um select visível; sem opções aparecia
    vazio no formulário de edição de categoria."""
    from models.schemas import TABLE_MAP
    from models.ui_schema import get_form_fields

    cfg = TABLE_MAP["categories"]
    fields = {f["name"]: f for f in get_form_fields(cfg["schema"], cfg, "categories")}
    tipo_field = fields["tipo_catalogo"]

    assert tipo_field["enum_options"]
    assert "almofada" in tipo_field["enum_options"]
    assert tipo_field["enum_labels"].get("almofada")


def test_category_slug_preset_does_not_veto_an_explicit_family():
    """CATEGORY_DEFINITIONS só dá predefinições. Antes, uma categoria chamada
    "Assentos" com outra família era recusada com um erro enganador — o que
    contrariava o CRUD livre de categorias."""
    from models.schemas import Categoria

    cat = Categoria(nome="Assentos", imagem="https://x/i.png", tipo_catalogo="toalha_mesa")
    assert cat.slug == "assentos"
    assert cat.tipo_catalogo == "toalha_mesa"


def test_category_without_explicit_family_still_inherits_preset():
    from models.schemas import Categoria

    cat = Categoria(nome="Assentos", imagem="https://x/i.png")
    assert cat.tipo_catalogo == "assento"
    assert cat.carrinho_step == 12


def test_storefront_page_limit_covers_the_whole_catalogue():
    """Nenhum chamador envia `limit` e não há "ver mais": o valor por omissão
    é a página que o cliente vê, por isso tem de ficar acima de qualquer
    categoria plausível em vez de truncar em silêncio."""
    from core.catalog_storefront import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT

    assert DEFAULT_PAGE_LIMIT >= 100
    assert MAX_PAGE_LIMIT >= DEFAULT_PAGE_LIMIT
