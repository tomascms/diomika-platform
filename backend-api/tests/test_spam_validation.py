"""Testes unitários leves — anti-spam e schema."""


def _honeypot_triggered(website: str | None) -> bool:
    return bool(website and str(website).strip())


def test_honeypot_empty_passes():
    assert not _honeypot_triggered(None)
    assert not _honeypot_triggered("")
    assert not _honeypot_triggered("   ")


def test_honeypot_filled_blocks():
    assert _honeypot_triggered("http://spam.example")


def test_catalog_types_include_assentos():
    from models.catalog_registry import CATALOG_TYPES, all_product_tables, all_model_tables

    assert "assento" in CATALOG_TYPES
    assert "assento" in all_product_tables()
    assert "modelos_assentos" in all_model_tables()


def test_table_map_assentos():
    from models.schemas import TABLE_MAP

    for key in ("assento", "modelos_assentos"):
        assert key in TABLE_MAP, f"missing TABLE_MAP[{key}]"


def test_public_category_fields():
    from core.public_api import public_category

    row = {
        "id": "1",
        "nome": "Test",
        "slug": "test",
        "imagem": "https://x/y.png",
        "tipo_catalogo": "almofada",
        "carrinho_step": 6,
        "carrinho_min": 6,
        "visibilidade": True,
        "created_at": "now",
    }
    pub = public_category(row)
    assert "visibilidade" not in pub
    assert pub["nome"] == "Test"


def test_turnstile_requires_secret_in_production(monkeypatch):
    import pytest
    from core.config import get_settings
    from utils import turnstile

    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="indisponível"):
        turnstile.verify_turnstile("token", "127.0.0.1")

    get_settings.cache_clear()
    monkeypatch.setenv("DIOMIKA_ENV", "development")
