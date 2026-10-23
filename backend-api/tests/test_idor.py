"""Anti-IDOR: recursos sensíveis por ID não são públicos."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from core.config import get_settings

# 400 = TrustedHost (app já importada em modo production noutro teste)
# 401/403 = auth/authz; 404 = rota inexistente — nenhum é leak de dados
_DENIED = (400, 401, 403, 404)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "development")
    monkeypatch.setenv("API_SECRET_KEY", "k" * 32)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "sk")
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "turnstile")
    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:8001")
    monkeypatch.delenv("DIOMIKA_BETA", raising=False)
    get_settings.cache_clear()
    from main import app

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def test_unauth_cannot_fetch_orcamento_pdf_by_id(client):
    rid = str(uuid.uuid4())
    resp = client.get(f"/orcamentos/{rid}/pdf")
    assert resp.status_code in _DENIED


def test_unauth_cannot_fetch_contacto_by_id(client):
    rid = str(uuid.uuid4())
    resp = client.get(f"/contacto/{rid}")
    assert resp.status_code in _DENIED


def test_unauth_cannot_fetch_encomenda_pdf_by_id(client):
    rid = str(uuid.uuid4())
    resp = client.get(f"/encomendas-internas/{rid}/pdf")
    assert resp.status_code in _DENIED


def test_unauth_cannot_crud_pedido_by_id(client):
    rid = str(uuid.uuid4())
    resp = client.get(f"/admin/crud/pedidos_orcamento/{rid}")
    assert resp.status_code in _DENIED


def test_unauth_cannot_list_contacto_inbox(client):
    resp = client.get("/contacto")
    assert resp.status_code in _DENIED


def test_hidden_category_returns_empty_catalog(monkeypatch):
    """UUID de categoria oculta não deve listar modelos (IDOR de soft-hide)."""
    from core import catalog_storefront as cs

    monkeypatch.setattr(cs, "_require_public_category", lambda _id: False)
    out = cs.catalogue_models_for_tipo("almofada", str(uuid.uuid4()))
    assert out == []
