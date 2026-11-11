from models.catalog_registry import PRODUCT_MODEL_COLORS_TABLE, admin_list_select_query


def test_lista_de_cores_do_modelo_traz_a_imagem():
    # O formulário do modelo mostra a foto guardada de cada cor. Sem `imagem` no select, a cor chegava sem foto e
    # gravar pedia a imagem outra vez.
    cols = [c.strip() for c in admin_list_select_query(PRODUCT_MODEL_COLORS_TABLE).split(",")]
    assert "imagem" in cols
