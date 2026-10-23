"""Testes de segurança — auth, headers, validação."""

import secrets

from core.config import get_settings


def test_api_key_required_in_production(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.setenv("API_SECRET_KEY", "test-secret-key")
    get_settings.cache_clear()
    assert get_settings().api_key_required is True
    get_settings.cache_clear()


def test_api_key_scopes_resolve(monkeypatch):
    monkeypatch.setenv("API_SECRET_KEY", "A" * 32)
    monkeypatch.setenv("API_OPS_KEY", "O" * 32)
    monkeypatch.setenv("API_CATALOG_KEY", "C" * 32)
    monkeypatch.setenv("API_PEDIDOS_KEY", "P" * 32)
    monkeypatch.setenv("API_MENSAGENS_KEY", "M" * 32)
    from core.auth import resolve_role

    assert resolve_role("A" * 32) == "admin"
    assert resolve_role("O" * 32) == "ops"
    assert resolve_role("C" * 32) == "catalog"
    assert resolve_role("P" * 32) == "pedidos"
    assert resolve_role("M" * 32) == "mensagens"
    assert resolve_role("wrong") is None


def test_docs_disabled_in_production(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.setenv("API_BASE_URL", "https://api.diomika.com")
    get_settings.cache_clear()
    assert get_settings().docs_enabled is False
    get_settings.cache_clear()


def test_docs_disabled_when_public_https_base(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "development")
    monkeypatch.setenv("API_BASE_URL", "https://api.diomika.com")
    get_settings.cache_clear()
    assert get_settings().docs_enabled is False
    get_settings.cache_clear()


def test_docs_enabled_local_http_by_default(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "development")
    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:8001")
    monkeypatch.delenv("DIOMIKA_ENABLE_DOCS", raising=False)
    get_settings.cache_clear()
    assert get_settings().docs_enabled is True
    get_settings.cache_clear()


def test_api_key_required_when_secret_set(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "development")
    monkeypatch.setenv("API_SECRET_KEY", "dev-key")
    get_settings.cache_clear()
    assert get_settings().api_key_required is True
    get_settings.cache_clear()


def test_compare_digest_timing_safe():
    a = "correct-key"
    b = "correct-key"
    c = "wrong-key"
    assert secrets.compare_digest(a, b)
    assert not secrets.compare_digest(a, c)


def test_api_key_required_in_beta(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.setenv("DIOMIKA_BETA", "1")
    monkeypatch.delenv("API_SECRET_KEY", raising=False)
    get_settings.cache_clear()
    assert get_settings().api_key_required is True
    get_settings.cache_clear()


def test_orcamento_requires_idempotency_in_production(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.setenv("DIOMIKA_BETA", "1")
    monkeypatch.setenv("API_SECRET_KEY", "k" * 32)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "sk")
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "turnstile")
    # TrustedHost em produção rejeita Host: testserver — usar host permitido
    monkeypatch.setenv("ALLOWED_HOSTS", "api.diomika.com")
    monkeypatch.setenv("CORS_ORIGINS", "https://www.diomika.com")
    get_settings.cache_clear()

    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app, base_url="https://api.diomika.com")
    resp = client.post(
        "/orcamentos",
        json={
            "nome": "Teste",
            "email": "test@example.com",
            "linhas": [{"ean": "1234567890123", "numero_cor": 1, "quantidade": 1}],
        },
    )
    assert resp.status_code == 400
    assert "Idempotency" in resp.json().get("detail", "")
    get_settings.cache_clear()


def test_production_rejects_turnstile_test_keys(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.delenv("DIOMIKA_BETA", raising=False)
    monkeypatch.setenv("API_SECRET_KEY", "k" * 32)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "sk")
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "1x0000000000000000000000000000000AA")
    monkeypatch.setenv("VITE_TURNSTILE_SITE_KEY", "1x00000000000000000000AA")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.diomika.com")
    monkeypatch.setenv("API_BASE_URL", "https://api.diomika.com")
    monkeypatch.setenv("CORS_ORIGINS", "https://www.diomika.com")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("SUPABASE_STORAGE_PRIVATE", "1")
    get_settings.cache_clear()
    settings = get_settings()
    try:
        settings.validate_startup()
        raised = False
    except SystemExit:
        raised = True
    assert raised
    get_settings.cache_clear()


def test_production_startup_requires_turnstile(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.setenv("API_SECRET_KEY", "k" * 32)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "sk")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    monkeypatch.setenv("CORS_ORIGINS", "https://loja.example.com")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.example.com")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("SUPABASE_STORAGE_PRIVATE", "1")
    get_settings.cache_clear()
    settings = get_settings()
    try:
        settings.validate_startup()
        raised = False
    except SystemExit:
        raised = True
    assert raised
    get_settings.cache_clear()
