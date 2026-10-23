"""Categoria é CRUD real: qualquer tipo_catalogo registado, sem limite a uma
categoria por família nem a uma lista fixa de slugs predefinidos."""
from __future__ import annotations


def test_categoria_accepts_any_registered_tipo_with_custom_slug():
    from models.schemas import Categoria

    cat = Categoria(nome="Almofadas de Natal", imagem="https://x/img.png", tipo_catalogo="almofada")
    assert cat.slug == "almofadas-de-natal"
    assert cat.tipo_catalogo == "almofada"
    assert cat.carrinho_step == 6


def test_categoria_rejects_unregistered_tipo():
    import pytest
    from pydantic import ValidationError

    from models.schemas import Categoria

    with pytest.raises(ValidationError):
        Categoria(nome="Mantas", imagem="https://x/img.png", tipo_catalogo="manta_inexistente")


def test_two_categories_can_share_the_same_tipo_catalogo():
    """Antes do refactor só podia existir 1 categoria por tipo_catalogo
    (CATEGORY_DEFINITIONS tinha 1 slug por tipo); agora não há essa restrição
    ao nível do schema — a 'categoria é CRUD falso' deixou de ser verdade."""
    from models.schemas import Categoria

    a = Categoria(nome="Almofadas", imagem="https://x/a.png", tipo_catalogo="almofada")
    b = Categoria(nome="Almofadas Outlet", imagem="https://x/b.png", tipo_catalogo="almofada")
    assert a.tipo_catalogo == b.tipo_catalogo == "almofada"
    assert a.slug != b.slug


def test_categories_available_tipos_lists_all_twelve_families():
    from routes.system import categories_available_tipos

    out = categories_available_tipos()
    tipos = {t["tipo"] for t in out["tipos"]}
    assert len(tipos) == 12
    assert "almofada" in tipos and "regional" in tipos
