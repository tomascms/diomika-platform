"""Envio pela Gmail API: usado quando há GMAIL_*; invalid_grant dá alerta e não fica em silêncio."""
import asyncio
import base64
from unittest.mock import MagicMock, patch

import pytest

from utils import email_sender, gmail_api


@pytest.fixture
def gmail_env(monkeypatch):
    for k, v in {"GMAIL_CLIENT_ID": "id", "GMAIL_CLIENT_SECRET": "s", "GMAIL_REFRESH_TOKEN": "r",
                 "MAIL_FROM": "loja@exemplo.pt"}.items():
        monkeypatch.setenv(k, v)
    for k in ("MAIL_SERVER", "MAIL_USERNAME", "MAIL_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    gmail_api._cache.update(token="", expires=0.0)


def _resp(status, body):
    r = MagicMock(status_code=status)
    r.json.return_value = body
    r.raise_for_status.side_effect = None if status < 400 else RuntimeError(status)
    return r


def test_sender_uses_gmail_api_without_smtp(gmail_env):
    calls = []

    def fake_post(url, **kw):
        calls.append((url, kw))
        return _resp(200, {"access_token": "t", "expires_in": 3600} if "token" in url else {"id": "m"})

    with patch.object(gmail_api.httpx, "post", side_effect=fake_post), patch.object(
        email_sender.smtplib, "SMTP", side_effect=AssertionError("não deve usar SMTP")
    ):
        assert asyncio.run(email_sender.send_email_async("c@exemplo.pt", "Olá", "corpo")) is True
    url, kw = calls[-1]
    assert url == gmail_api.SEND_URL and kw["headers"]["Authorization"] == "Bearer t"
    raw = base64.urlsafe_b64decode(kw["json"]["raw"]).decode()
    assert "To: c@exemplo.pt" in raw and "From: loja@exemplo.pt" in raw


def test_revoked_authorization_alerts(gmail_env):
    with patch.object(gmail_api.httpx, "post", return_value=_resp(400, {"error": "invalid_grant"})), patch.object(
        gmail_api, "send_alert"
    ) as alert:
        with pytest.raises(gmail_api.GmailAuthError):
            gmail_api.access_token()
    assert alert.called and alert.call_args.kwargs["severity"] == "critical"


def test_not_configured_keeps_smtp(monkeypatch):
    monkeypatch.delenv("GMAIL_REFRESH_TOKEN", raising=False)
    assert gmail_api.configured() is False
