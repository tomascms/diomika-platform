from models.catalog_attributes import CATEGORY_ATTRIBUTE_SCHEMAS


def test_cinto_e_um_produto_por_modelo_sem_picker():
    # Os cintos têm um EAN por modelo e não têm variante a escolher. Com «variantes» e sem picker, a loja não mostra
    # nenhum produto e a página do modelo diz que já não está disponível.
    cinto = CATEGORY_ATTRIBUTE_SCHEMAS["cinto"]
    assert cinto["storefront_mode"] == "unico"
    assert "storefront_picker" not in cinto
