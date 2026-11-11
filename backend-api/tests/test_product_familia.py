"""Criar um produto (EAN) sem o campo «tipo_catalogo» no corpo: a família vem da tabela (não do formulário)."""
from models.catalog_registry import all_product_tables, tipo_for_table
from routes.admin_crud import _enrich_create_payload


def test_produto_recebe_a_familia_da_tabela():
    table = sorted(all_product_tables())[0]
    body = _enrich_create_payload(table, {"ean": "5600000000013", "id_modelo": "x"})
    assert body["tipo_catalogo"] == tipo_for_table(table)


def test_familia_do_corpo_nao_substitui_a_da_tabela():
    table = sorted(all_product_tables())[0]
    body = _enrich_create_payload(table, {"tipo_catalogo": "outra"})
    assert body["tipo_catalogo"] == tipo_for_table(table)


def test_tabela_que_nao_e_produto_fica_como_esta():
    body = _enrich_create_payload("categories", {"nome": "X"})
    assert body == {"nome": "X"}
