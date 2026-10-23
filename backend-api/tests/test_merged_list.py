"""Testes da lista merged do admin (filtro categoria/modelo/tipo).

Esquema unificado: 1 tabela física por vista (product_models / product_variants),
filtrada por categoria/modelo/tipo_catalogo — já não há fan-out a N tabelas."""

from unittest.mock import MagicMock, patch

from routes.catalog_generic import _load_merged_page, _resolve_merged_tipos


def _mock_db_with(rows: list[dict], count: int | None = None):
    mock_db = MagicMock()
    chain = mock_db.table.return_value.select.return_value
    final = chain.eq.return_value.in_.return_value.order.return_value.range.return_value
    exec_result = MagicMock()
    exec_result.data = rows
    exec_result.count = count
    # Qualquer combinação de .eq/.in_/.order/.range deve devolver o mesmo mock encadeável
    for attr in ("eq", "in_", "order", "range"):
        getattr(chain, attr).return_value = chain
    chain.execute.return_value = exec_result
    return mock_db


def test_load_merged_page_produtos_no_models_in_category_returns_empty_no_crash():
    """Categoria sem modelos: não deve tentar listar variantes (e não deve rebentar)."""
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    with patch("routes.catalog_generic.get_db", return_value=mock_db):
        rows, total = _load_merged_page(
            view_key="produtos",
            visible_only=False,
            limit=20,
            offset=0,
            categoria_id="cat-sem-modelos",
            modelo_id=None,
            tipos=None,
        )
    assert rows == []
    assert total == 0


def test_resolve_merged_tipos_none_means_no_filter():
    assert _resolve_merged_tipos(None) is None
    assert _resolve_merged_tipos("") is None


def test_resolve_merged_tipos_aggregated_expands_to_physical_tipos():
    tipos = _resolve_merged_tipos("material_cozinha")
    assert set(tipos) == {"avental", "luva", "pega", "pano_cozinha"}


def test_resolve_merged_tipos_single_valid_tipo():
    assert _resolve_merged_tipos("almofada") == ["almofada"]


def test_resolve_merged_tipos_unknown_tipo_returns_empty_list():
    assert _resolve_merged_tipos("inexistente") == []


def test_load_merged_page_modelos_view_filters_by_category_and_tipo():
    rows = [
        {
            "id": "m1",
            "nome": "Almofada X",
            "tipo_catalogo": "almofada",
            "visibilidade": True,
            "categories": {"nome": "Almofadas"},
        }
    ]
    mock_db = _mock_db_with(rows, count=1)
    with patch("routes.catalog_generic.get_db", return_value=mock_db):
        out_rows, total = _load_merged_page(
            view_key="modelos",
            visible_only=True,
            limit=20,
            offset=0,
            categoria_id="cat-1",
            modelo_id=None,
            tipos=["almofada"],
        )
    assert total == 1
    assert out_rows[0]["_tipo_catalogo"] == "almofada"
    assert out_rows[0]["_categoria_label"] == "Almofadas"
    assert out_rows[0]["_ptable"] == "modelos_almofadas"
