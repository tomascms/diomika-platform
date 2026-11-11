"""FE-14: o assunto do formulário de contacto é opcional (o email e a mensagem chegam para responder)."""
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


def _saved_subject(api):
    api.saga.assert_awaited_once()
    return api.saga.await_args.args[0]["assunto"]


def test_contact_without_subject_is_accepted(api):
    response = api.client.post("/contacto", json=_MESSAGE)

    assert response.status_code == 200
    assert _saved_subject(api) is None


@pytest.mark.parametrize("blank", ["", "   ", None], ids=["vazio", "espaços", "null"])
def test_contact_with_blank_subject_is_stored_as_null(api, blank):
    response = api.client.post("/contacto", json={**_MESSAGE, "assunto": blank})

    assert response.status_code == 200
    assert _saved_subject(api) is None


def test_contact_with_subject_keeps_it(api):
    assert api.client.post("/contacto", json={**_MESSAGE, "assunto": " Acesso aos meus dados "}).status_code == 200
    assert _saved_subject(api) == "Acesso aos meus dados"


def test_contact_subject_still_limited_to_200_characters(api):
    assert api.client.post("/contacto", json={**_MESSAGE, "assunto": "a" * 201}).status_code == 422
    api.saga.assert_not_awaited()


def test_contact_message_is_still_required(api):
    assert api.client.post("/contacto", json={"nome": "Ana Silva", "email": "ana@example.com"}).status_code == 422
    api.saga.assert_not_awaited()


@pytest.fixture
def saga_run():
    """Corre a saga com a BD e o SMTP substituídos; devolve a linha que se gravaria e o email para a equipa."""
    from core.saga import contact_saga

    inserted: list[dict] = []
    db = MagicMock()
    db.table.return_value.insert.side_effect = lambda row: (inserted.append(row), MagicMock())[1]
    send = AsyncMock(return_value=True)

    def run(**fields):
        with patch.object(contact_saga, "get_db", return_value=db), patch.object(
            contact_saga, "saga_log_async", AsyncMock()
        ), patch.object(contact_saga, "contact_notify_email", return_value="equipa@example.test"), patch.object(
            contact_saga, "send_email_async", send
        ):
            asyncio.run(contact_saga.run_contact_submission_saga({**_MESSAGE, "contacto": None, **fields}))
        return inserted[0], send.await_args.kwargs

    return run


def test_message_without_subject_is_stored_and_emailed_as_no_subject(saga_run):
    row, email = saga_run(assunto=None)

    assert row["assunto"] == "Sem assunto"  # a coluna e a lista do backoffice esperam texto, nunca NULL
    assert "— Sem assunto [Ref: #" in email["subject"]
    assert "Assunto: Sem assunto\n" in email["body"]
    assert "None" not in email["subject"] + email["body"]


def test_message_with_subject_keeps_it(saga_run):
    row, email = saga_run(assunto="Acesso aos meus dados")

    assert row["assunto"] == "Acesso aos meus dados"
    assert "— Acesso aos meus dados [Ref: #" in email["subject"]
