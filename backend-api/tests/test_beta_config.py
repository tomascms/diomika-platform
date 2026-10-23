"""Configuração modo beta."""
from __future__ import annotations


def test_beta_skips_strict_cors(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.setenv("DIOMIKA_BETA", "1")
    monkeypatch.setenv("API_SECRET_KEY", "test-key-with-enough-length-32ch")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "key")
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "turnstile-test")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.diomika.com")

    from core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    settings.validate_startup()
    assert settings.is_beta
