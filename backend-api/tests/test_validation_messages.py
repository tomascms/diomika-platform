"""FE-09, API-09, SEG-04, A11Y-07: erros de validação em português e ids inválidos sem tocar na BD.

A BD, o Turnstile e o SMTP são substituídos ou nunca chegam a ser usados: nada sai da máquina.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from types import SimpleNamespace
from typing import Annotated, get_args, get_origin
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import AfterValidator

LINHA = {"ean": "5606044000012", "numero_cor": 1, "quantidade": 12}
OK = {"nome": "Ana Silva", "email": "ana@example.com", "linhas": [LINHA]}
MODEL_ID = "3f2a9c1b-6d4e-4f10-9a77-0c5d2e8b1a34"

# Palavras do inglês que o Pydantic usa nas mensagens: nenhuma pode chegar à loja.
ENGLISH = re.compile(
    r"\b(should|field required|input|valid|string|value is|must|invalid|expected|not a|at least|at most|missing)\b",
    re.IGNORECASE,
)


@pytest.fixture
def api(monkeypatch):
    """App completa; as sagas e a BD substituídas, para que um pedido válido não saia da máquina."""
    import main
    from core import rate_limit
    from core.config import get_settings

    monkeypatch.setenv("DIOMIKA_ENV", "development")
    monkeypatch.delenv("DIOMIKA_BETA", raising=False)
    get_settings.cache_clear()
    monkeypatch.setattr(rate_limit, "_hits", defaultdict(list))
    monkeypatch.setattr("utils.turnstile.verify_turnstile", lambda token, remote_ip=None: None)
    monkeypatch.setattr("routes.orcamentos.validate_order_lines", lambda linhas: None)
    monkeypatch.setattr(
        "routes.orcamentos.run_orcamento_submission_saga",
        AsyncMock(return_value=SimpleNamespace(pedido_id=MODEL_ID, status="Nova")),
    )
    monkeypatch.setattr(
        "routes.contact.run_contact_submission_saga",
        AsyncMock(return_value=SimpleNamespace(email_sent=True, status="Nova")),
    )
    yield TestClient(main.app, base_url="http://localhost")
    get_settings.cache_clear()


def _errors(response) -> dict[str, str]:
    """campo → mensagem; confirma que cada erro só tem `type`, `loc` e `msg`."""
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    for item in detail:
        assert set(item) == {"type", "loc", "msg"}  # sem `input` (eco do que se escreveu), `ctx` nem `url`
    # O nome do campo é o último texto de `loc` (um JSON mal formado só tem a posição do erro: fica «body»).
    return {
        next((p for p in reversed(item["loc"]) if isinstance(p, str) and p != "body"), "body"): item["msg"]
        for item in detail
    }


# --- Mensagens em português --------------------------------------------------------------------------


def test_missing_fields_are_asked_for_in_portuguese(api):
    errors = _errors(api.post("/orcamentos", json={}))

    assert errors == {
        "nome": "Indique o nome.",
        "email": "Indique o email.",
        "linhas": "Indique as linhas do pedido.",
    }


def test_too_short_and_bad_email_in_the_quote_form(api):
    errors = _errors(api.post("/orcamentos", json={"nome": "A", "email": "a@b", "linhas": [LINHA]}))

    assert errors == {
        "nome": "O nome: mínimo de 2 caracteres.",
        "email": "Indique um email válido, por exemplo nome@empresa.pt.",
    }


def test_too_long_values_say_the_limit(api):
    errors = _errors(api.post("/orcamentos", json={**OK, "nome": "x" * 121, "observacoes": "y" * 5001}))

    assert errors == {
        "nome": "O nome: máximo de 120 caracteres.",
        "observacoes": "As observações: máximo de 5000 caracteres.",
    }


def test_lists_numbers_patterns_and_choices(api):
    assert _errors(api.post("/orcamentos", json={**OK, "linhas": []})) == {
        "linhas": "As linhas do pedido: indique pelo menos 1.",
    }
    assert _errors(api.post("/orcamentos", json={**OK, "tipo_cliente": "revendedor"})) == {
        "tipo_cliente": "O tipo de cliente: valor não permitido.",
    }
    assert _errors(api.post("/orcamentos", json={**OK, "linhas": [{**LINHA, "ean": "123"}]})) == {
        "ean": "O EAN: formato inválido.",
    }
    assert _errors(api.post("/orcamentos", json={**OK, "linhas": [{**LINHA, "quantidade": 0}]})) == {
        "quantidade": "A quantidade: mínimo de 1.",
    }
    assert _errors(api.post("/orcamentos", json={**OK, "linhas": [{**LINHA, "numero_cor": "x"}]})) == {
        "numero_cor": "A cor: indique um número válido.",
    }


def test_contact_form_messages(api):
    errors = _errors(api.post("/contacto", json={"nome": "Ana Silva", "email": "ana", "mensagem": "curta"}))

    assert errors == {
        "email": "Indique um email válido, por exemplo nome@empresa.pt.",
        "mensagem": "A mensagem: mínimo de 10 caracteres.",
    }


def test_a_body_that_is_not_json(api):
    response = api.post("/orcamentos", content="{ isto não é json", headers={"Content-Type": "application/json"})

    assert _errors(response) == {"body": "O pedido não está bem formado."}


def test_custom_messages_written_in_the_code_pass_through(api):
    """O NIF português com o dígito errado leva a frase que o código escreveu, não «Value error, …»."""
    errors = _errors(api.post("/orcamentos", json={**OK, "nif": "508651558"}))

    assert errors == {"nif": "NIF inválido: o dígito de controlo não confere. Confira os 9 dígitos."}


def test_no_message_is_in_english_and_nothing_typed_is_echoed(api):
    typed = "um-valor-que-o-visitante-escreveu-9f3a"
    bodies = [
        {},
        {"nome": "A", "email": typed, "linhas": []},
        {**OK, "nome": typed * 20},
        {**OK, "tipo_cliente": typed},
        {**OK, "linhas": [{"ean": typed, "numero_cor": typed, "quantidade": typed}]},
    ]
    for body in bodies:
        response = api.post("/orcamentos", json=body)
        for message in _errors(response).values():
            assert not ENGLISH.search(message), message
        assert typed not in response.text


# --- Ids que não são UUID --------------------------------------------------------------------------


@pytest.fixture
def no_db(monkeypatch):
    """Qualquer ida à BD, à cache ou ao catálogo a partir de uma rota de catálogo faz o teste falhar."""

    def boom(*args, **kwargs):
        raise AssertionError("um id inválido não pode chegar à BD nem à cache")

    for name in ("get_db", "get_or_set", "catalogue_for_category", "model_detail_for_tipo"):
        monkeypatch.setattr(f"routes.catalog_generic.{name}", boom)


BAD_ID_URLS = [
    "/catalogo/modelo-detalhe/nao-e-uuid",
    "/catalogo/almofada/modelo-detalhe/nao-e-uuid",
    "/catalogo/almofada/modelos-catalogo/nao-e-uuid",
    "/categorias/nao-e-uuid",
]


@pytest.mark.parametrize("url", BAD_ID_URLS)
def test_invalid_id_is_422_in_portuguese_without_touching_the_database(api, no_db, caplog, url):
    caplog.set_level(logging.DEBUG)
    response = api.get(url)

    assert response.status_code == 422
    assert [item["msg"] for item in response.json()["detail"]] == ["Identificador inválido."]
    # Um registo de erro seria um evento no Sentry (LoggingIntegration, event_level=ERROR): SEG-04.
    assert [r for r in caplog.records if r.levelno >= logging.ERROR] == []
    assert "nao-e-uuid" not in response.text


def test_invalid_id_is_not_cached(api, no_db):
    """Antes `/catalogo/almofada/modelos-catalogo/nao-e-uuid` devolvia 200 `[]`, guardado em cache."""
    assert api.get("/catalogo/almofada/modelos-catalogo/nao-e-uuid").status_code == 422


def test_a_valid_id_reaches_the_route_in_canonical_form(api, monkeypatch):
    keys: list[str] = []

    def fake_get_or_set(key, ttl, loader):
        keys.append(key)
        return {"ok": True}

    monkeypatch.setattr("routes.catalog_generic.get_or_set", fake_get_or_set)

    for url in (f"/catalogo/modelo-detalhe/{MODEL_ID.upper()}", f"/catalogo/modelo-detalhe/{MODEL_ID}"):
        assert api.get(url).status_code == 200

    # Maiúsculas e minúsculas dão a mesma chave de cache.
    assert keys == [f"catalog:modelo-auto:{MODEL_ID}"] * 2


@pytest.mark.parametrize(
    "path",
    [
        "/orcamentos/{id}/pdf",
        "/contacto/{id}",
        "/encomendas-internas/{id}/pdf",
        "/admin/crud/categories/{id}",
        "/system/order-picker/{id}",
    ],
)
def test_internal_routes_refuse_an_invalid_id_before_anything_else(api, caplog, path):
    """Rotas do backoffice: o id é validado antes de a rota correr, por isso nem a autenticação importa para o 422."""
    caplog.set_level(logging.DEBUG)
    response = api.get(path.format(id="nao-e-uuid"))

    assert response.status_code in (401, 403, 404, 422)  # 401/403: a autenticação corre primeiro; nunca 500
    assert [r for r in caplog.records if r.levelno >= logging.ERROR] == []


# --- Revisão das rotas: nenhum id chega à BD como texto livre ---------------------------------------

ID_NAME = re.compile(r"^(id|id_\w+|\w+_id)$")
# Validados à mão (UUID(...) → 400) antes de qualquer consulta.
CHECKED_BY_HAND = {("/catalogo/admin/merged/{view_key}", "categoria_id"), ("/catalogo/admin/merged/{view_key}", "modelo_id")}


def _is_uuid_typed(annotation, metadata) -> bool:
    if annotation is UUID or any(isinstance(m, AfterValidator) for m in metadata):
        return True
    # pydantic >= 2.11 deixa o Annotated[...] na própria anotação em vez de o abrir em `metadata`.
    if get_origin(annotation) is Annotated and any(isinstance(m, AfterValidator) for m in annotation.__metadata__):
        return True
    for arg in get_args(annotation):
        if arg is UUID or (
            get_origin(arg) is Annotated and any(isinstance(m, AfterValidator) for m in arg.__metadata__)
        ):
            return True
    return False


def _id_params(dependant):
    for param in (*dependant.path_params, *dependant.query_params):
        if ID_NAME.match(param.name):
            yield param
    for sub in dependant.dependencies:
        yield from _id_params(sub)


def test_every_id_parameter_is_typed_as_a_uuid():
    """SEG-04/API-09: «rever as rotas com `id: str` que vão à BD». Um parâmetro novo com `id: str` reprova aqui."""
    import main

    loose = []
    for route in main.app.routes:
        if not isinstance(route, APIRoute):
            continue
        for param in _id_params(route.dependant):
            info = param.field_info
            if (route.path, param.name) in CHECKED_BY_HAND:
                continue
            if not _is_uuid_typed(info.annotation, info.metadata):
                loose.append(f"{route.path} · {param.name}")
    assert loose == [], "parâmetros de id sem tipo UUID (use UuidStr de core/path_ids.py): " + ", ".join(loose)


# --- Rotas do backoffice (com a autenticação dispensada: o que se vê é a validação do id) -------------


@pytest.fixture
def admin(api, monkeypatch):
    """O backoffice autenticado, com a BD proibida: só interessa o que a rota faz com o id."""
    from core.auth import require_admin
    from core.local_only import admin_must_be_local

    def boom(*args, **kwargs):
        raise AssertionError("um id inválido não pode chegar à BD")

    monkeypatch.setattr("routes.admin_crud._db_table", boom)
    app = api.app  # TestClient.app
    app.dependency_overrides[admin_must_be_local] = lambda: None
    app.dependency_overrides[require_admin] = lambda: "admin"
    yield api
    app.dependency_overrides.pop(admin_must_be_local, None)
    app.dependency_overrides.pop(require_admin, None)


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/admin/crud/categories/nao-e-uuid"),
        ("put", "/admin/crud/categories/nao-e-uuid"),
        ("patch", "/admin/crud/categories/nao-e-uuid/visibility"),
        ("post", "/admin/crud/categories/nao-e-uuid/publish"),
        ("patch", "/admin/crud/pedidos_orcamento/nao-e-uuid/lida"),
        ("delete", "/admin/crud/categories/nao-e-uuid"),
        ("get", "/admin/crud/modelos_almofadas?id_modelo=nao-e-uuid"),
        ("get", "/admin/crud/modelos_almofadas/options?id_modelo=nao-e-uuid"),
    ],
)
def test_backoffice_routes_refuse_an_invalid_id_before_the_database(admin, method, path):
    response = getattr(admin, method)(path, **({"json": {}} if method in ("put", "patch", "post") else {}))

    assert response.status_code == 422, response.text
    assert [item["msg"] for item in response.json()["detail"]] == ["Identificador inválido."]


def test_options_is_not_swallowed_by_the_typed_record_id(admin, monkeypatch):
    """`/{tabela}/options` é declarada antes de `/{tabela}/{record_id}`: «options» não é um id, mas não pode dar 422."""
    monkeypatch.setattr("routes.admin_crud.relation_options", lambda *a, **k: [{"id": MODEL_ID, "label": "x"}])

    response = admin.get("/admin/crud/categories/options")

    assert response.status_code == 200
    assert response.json() == {"items": [{"id": MODEL_ID, "label": "x"}]}
