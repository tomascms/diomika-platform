from uuid import uuid4

import pytest
from models.catalog_registry import PRODUCT_MODEL_COLORS_TABLE, admin_list_select_query
from models.schemas import ProductModelColor
from core.catalog_bundle import build_bundle  # noqa: F401  (o módulo tem de carregar sem BD)


def _cor(**extra):
    return ProductModelColor(id_modelo=uuid4(), numero=12, nome="Azul Ciano", **extra)


def test_uma_cor_aceita_varias_imagens_por_ordem():
    cor = _cor(imagens=["a.jpg", "b.jpg", "c.jpg"])
    assert cor.imagens == ["a.jpg", "b.jpg", "c.jpg"]
    assert cor.imagem == "a.jpg"  # a principal é a primeira


def test_imagem_antiga_continua_a_funcionar():
    cor = _cor(imagem="a.jpg")  # pedido antigo: só `imagem`
    assert cor.imagens == ["a.jpg"]
    assert cor.imagem == "a.jpg"


def test_repetidas_e_vazias_saem_e_a_ordem_fica():
    cor = _cor(imagem="a.jpg", imagens=["b.jpg", " ", "a.jpg", "", "c.jpg"])
    assert cor.imagens == ["a.jpg", "b.jpg", "c.jpg"]


def test_cor_sem_imagem_fica_vazia_como_antes():
    cor = _cor()
    assert cor.imagens == [] and cor.imagem == ""


def test_lista_de_cores_traz_as_imagens_todas():
    cols = [c.strip() for c in admin_list_select_query(PRODUCT_MODEL_COLORS_TABLE).split(",")]
    assert "imagens" in cols and "imagem" in cols


def test_lista_de_produtos_traz_o_made_in_do_modelo():
    # A etiqueta (QR) do produto lê o país de fabrico do modelo; sem ele na lista o botão dizia «Falta o Made in».
    from models.catalog_registry import PRODUCT_VARIANTS_TABLE

    for embed in (False, True):
        sel = admin_list_select_query(PRODUCT_VARIANTS_TABLE, embed_category=embed)
        assert "made_in" in sel and "attributes" in sel
