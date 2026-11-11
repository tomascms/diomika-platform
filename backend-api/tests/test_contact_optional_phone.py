"""LEGAL-13: o telefone do formulário de contacto é opcional (RGPD art. 5.º/1 c): o email chega para responder)."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_MESSAGE = {
    "nome": "Ana Silva",
    "email": "ana@example.com",
    "assunto": "Pedido",
    "mensagem": "Gostaria de pedir um orçamento.",
}


@pytest.fixture
def api(monkeypatch):
    """App completa com o Turnstile e a saga substituídos: nada sai da máquina. `saga` regista o que se guardaria."""
    import main
    from core import rate_limit
    from core.config import get_settings

    monkeypatch.setenv("DIOMIKA_ENV", "development")
    monkeypatch.delenv("DIOMIKA_BETA", raising=False)
    get_settings.cache_clear()
    monkeypatch.setattr(rate_limit, "_hits", defaultdict(list))
    monkeypatch.setattr("utils.turnstile.verify_turnstile", lambda token, remote_ip=None: None)
    saga = AsyncMock(return_value=SimpleNamespace(email_sent=True, status="Nova"))
    monkeypatch.setattr("routes.contact.run_contact_submission_saga", saga)
    yield SimpleNamespace(client=TestClient(main.app, base_url="http://localhost"), saga=saga)
    get_settings.cache_clear()


def _saved_phone(api):
    api.saga.assert_awaited_once()
    return api.saga.await_args.args[0]["contacto"]


def test_contact_without_phone_is_accepted(api):
    response = api.client.post("/contacto", json=_MESSAGE)

    assert response.status_code == 200
    assert _saved_phone(api) is None  # a coluna `contacto` aceita NULL: nada de «» nem de «None» em texto


@pytest.mark.parametrize("blank", ["", "   ", None], ids=["vazio", "espaços", "null"])
def test_contact_with_blank_phone_is_stored_as_null(api, blank):
    response = api.client.post("/contacto", json={**_MESSAGE, "contacto": blank})

    assert response.status_code == 200
    assert _saved_phone(api) is None


def test_contact_with_phone_keeps_it(api):
    response = api.client.post("/contacto", json={**_MESSAGE, "contacto": " 912 345 678 "})

    assert response.status_code == 200
    assert _saved_phone(api) == "912 345 678"


def test_contact_phone_still_limited_to_20_characters(api):
    assert api.client.post("/contacto", json={**_MESSAGE, "contacto": "9" * 21}).status_code == 422
    api.saga.assert_not_awaited()


def test_notification_email_shows_a_dash_without_phone():
    """O email para a equipa não pode dizer «Contacto: None» quando o visitante não deu telefone."""
    from core.saga import contact_saga

    send = AsyncMock(return_value=True)
    with patch.object(contact_saga, "get_db", return_value=MagicMock()), patch.object(
        contact_saga, "saga_log_async", AsyncMock()
    ), patch.object(contact_saga, "contact_notify_email", return_value="equipa@example.test"), patch.object(
        contact_saga, "send_email_async", send
    ):
        asyncio.run(contact_saga.run_contact_submission_saga({**_MESSAGE, "contacto": None}))

    body = send.await_args.kwargs["body"]
    assert "Contacto: -\n" in body
    assert "None" not in body
