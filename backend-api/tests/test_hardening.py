"""Testes de hardening — outbox, idempotency, upload, proxy, startup."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


def test_outbox_fetch_pending_respects_next_retry_at():
    from core.outbox import fetch_pending

    mock_db = MagicMock()
    chain = mock_db.table.return_value
    chain.select.return_value.eq.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )

    with patch("core.outbox.get_db", return_value=mock_db):
        assert fetch_pending() == []

    chain.select.return_value.eq.assert_called_with("status", "pending")
    chain.select.return_value.eq.return_value.lte.assert_called_once()
    args = chain.select.return_value.eq.return_value.lte.call_args[0]
    assert args[0] == "next_retry_at"


def test_begin_idempotent_unavailable_on_db_error():
    from core.idempotency import IdempotencyUnavailable, begin_idempotent_request, get_cached_response

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.side_effect = RuntimeError(
        "db down"
    )

    with patch("core.idempotency.get_db", return_value=mock_db):
        with pytest.raises(IdempotencyUnavailable):
            get_cached_response("k1", "OP")
        assert begin_idempotent_request("k2", "OP") == "unavailable"


def test_upload_rejects_unknown_table():
    from routes.admin_crud import _allowed_upload_field

    assert _allowed_upload_field("tabela_inexistente", "imagem") is False


def test_trusted_proxy_ignores_spoofed_xff_without_trusted_peer():
    from core.rate_limit import get_client_ip

    class Client:
        host = "203.0.113.50"

    class Req:
        client = Client()
        headers = {"x-forwarded-for": "1.2.3.4"}

    with patch("core.rate_limit.trust_proxy_headers", return_value=True):
        assert get_client_ip(Req()) == "203.0.113.50"


def test_trusted_proxy_uses_xff_from_trusted_peer(monkeypatch):
    from core.rate_limit import get_client_ip

    monkeypatch.setenv("TRUSTED_PROXY_IPS", "127.0.0.1")

    class Client:
        host = "127.0.0.1"

    class Req:
        client = Client()
        headers = {"x-forwarded-for": "198.51.100.10, 127.0.0.1"}

    with patch("core.rate_limit.trust_proxy_headers", return_value=True):
        assert get_client_ip(Req()) == "198.51.100.10"


def test_production_rejects_ssl_insecure(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.delenv("DIOMIKA_BETA", raising=False)
    monkeypatch.setenv("API_SECRET_KEY", "k" * 32)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "sk")
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "real-turnstile-secret")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.diomika.com")
    monkeypatch.setenv("API_BASE_URL", "https://api.diomika.com")
    monkeypatch.setenv("CORS_ORIGINS", "https://www.diomika.com")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("SUPABASE_STORAGE_PRIVATE", "1")
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "1")
    monkeypatch.setenv("DIOMIKA_SSL_INSECURE", "1")
    from core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    with pytest.raises(SystemExit):
        settings.validate_startup()
    get_settings.cache_clear()


def test_production_rejects_admin_allow_remote(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.delenv("DIOMIKA_BETA", raising=False)
    monkeypatch.setenv("API_SECRET_KEY", "k" * 32)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "sk")
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "real-turnstile-secret")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.diomika.com")
    monkeypatch.setenv("API_BASE_URL", "https://api.diomika.com")
    monkeypatch.setenv("CORS_ORIGINS", "https://www.diomika.com")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("SUPABASE_STORAGE_PRIVATE", "1")
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "1")
    monkeypatch.delenv("DIOMIKA_SSL_INSECURE", raising=False)
    monkeypatch.setenv("ADMIN_ALLOW_REMOTE", "1")
    from core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    with pytest.raises(SystemExit):
        settings.validate_startup()
    get_settings.cache_clear()


def test_production_trusted_proxy_ips_required_when_trust_proxy(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.delenv("DIOMIKA_BETA", raising=False)
    monkeypatch.setenv("API_SECRET_KEY", "k" * 32)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "sk")
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "real-turnstile-secret")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.diomika.com")
    monkeypatch.setenv("API_BASE_URL", "https://api.diomika.com")
    monkeypatch.setenv("CORS_ORIGINS", "https://www.diomika.com")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("SUPABASE_STORAGE_PRIVATE", "1")
    monkeypatch.delenv("DIOMIKA_SSL_INSECURE", raising=False)
    monkeypatch.delenv("ADMIN_ALLOW_REMOTE", raising=False)
    monkeypatch.setenv("ADMIN_MFA_REQUIRED", "0")
    from core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("TRUST_PROXY", "1")
    monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)
    get_settings.cache_clear()
    with pytest.raises(SystemExit):
        get_settings().validate_startup()
    get_settings.cache_clear()

    monkeypatch.setenv("TRUSTED_PROXY_IPS", "127.0.0.1")
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://hooks.slack.com/services/T/B/X")
    get_settings.cache_clear()
    get_settings().validate_startup()
    get_settings.cache_clear()


def test_beta_allows_explicit_ssl_insecure_with_warning(monkeypatch, capsys):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.setenv("DIOMIKA_BETA", "1")
    monkeypatch.setenv("API_SECRET_KEY", "k" * 32)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "sk")
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "1x0000000000000000000000000000000AA")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.diomika.com")
    monkeypatch.setenv("DIOMIKA_SSL_INSECURE", "1")
    from core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    settings.validate_startup()  # nao aborta em beta; avisa
    err = capsys.readouterr().err
    assert "DIOMIKA_SSL_INSECURE" in err
    get_settings.cache_clear()
