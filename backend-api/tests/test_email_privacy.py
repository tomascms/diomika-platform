"""Emails mascarados nos logs e respostas agrupadas na mesma conversa."""
from __future__ import annotations

import asyncio
from unittest.mock import patch

from core.log_safe import redact_text


def test_logs_mask_emails():
    out = redact_text("Email enviado para joana.silva@cliente.pt e SMTP->a@b.com")
    assert "joana.silva" not in out
    assert "j***@cliente.pt" in out and "a***@b.com" in out


def test_reply_has_thread_headers(monkeypatch):
    for k, v in {"MAIL_SERVER": "smtp.test", "MAIL_USERNAME": "u", "MAIL_PASSWORD": "p", "MAIL_FROM": "loja@diomika.com"}.items():
        monkeypatch.setenv(k, v)
    sent = {}

    class FakeSMTP:
        def __init__(self, *a, **k): ...
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def ehlo(self): ...
        def starttls(self): ...
        def login(self, *a): ...
        def send_message(self, msg): sent["msg"] = msg

    from utils import email_sender

    with patch.object(email_sender.smtplib, "SMTP", FakeSMTP):
        assert asyncio.run(email_sender.send_email_async("c@x.pt", "Re: x", "ola", thread_id="abc"))
    msg = sent["msg"]
    assert msg["In-Reply-To"] == "<contacto-abc@diomika.com>" == msg["References"]
    assert msg["Message-ID"].endswith("@diomika.com>")
