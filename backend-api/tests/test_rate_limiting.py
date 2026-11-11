"""Tests for client IP resolution and the public-form rate limits."""
import pytest
from collections import defaultdict
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from fastapi import HTTPException
from starlette.requests import Request

# --- IP real do visitante (SEG-01 / API-02) ---------------------------------
# Produção: o cloudflared liga a 127.0.0.1:8000 e o docker-proxy entrega à API
# com o par 172.18.0.1; a Cloudflare reescreve CF-Connecting-IP em cada pedido.

DOCKER_GATEWAY = "172.18.0.1"


def _request(peer: str, headers: dict[str, str] | None = None) -> Request:
    scope = {
        "type": "http",
        "client": (peer, 50000),
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
    }
    return Request(scope)


@pytest.fixture
def trusted_gateway(monkeypatch):
    monkeypatch.setenv("TRUST_PROXY", "1")
    monkeypatch.setenv("TRUSTED_PROXY_IPS", f"127.0.0.1,::1,{DOCKER_GATEWAY}")


def test_client_ip_uses_cf_connecting_ip_from_trusted_peer(trusted_gateway):
    from core.rate_limit import get_client_ip

    request = _request(DOCKER_GATEWAY, {"CF-Connecting-IP": "203.0.113.9"})
    assert get_client_ip(request) == "203.0.113.9"


@pytest.mark.parametrize(
    "header, value",
    [
        pytest.param("X-Forwarded-For", "127.0.0.1", id="xff"),
        # A Cloudflare acrescenta o IP real DEPOIS do valor que o cliente enviou: o 1.º é forjável.
        pytest.param("X-Forwarded-For", "127.0.0.1, 203.0.113.9", id="xff-chain"),
        pytest.param("X-Real-IP", "127.0.0.1", id="x-real-ip"),
    ],
)
def test_client_ip_ignores_forged_xff(trusted_gateway, header, value):
    from core.rate_limit import get_client_ip

    request = _request(DOCKER_GATEWAY, {header: value})
    assert get_client_ip(request) == DOCKER_GATEWAY  # o par TCP; nunca o valor forjado


def test_client_ip_untrusted_peer_ignores_headers(trusted_gateway):
    from core.rate_limit import get_client_ip

    headers = {"CF-Connecting-IP": "203.0.113.9", "X-Forwarded-For": "203.0.113.10"}
    assert get_client_ip(_request("198.51.100.7", headers)) == "198.51.100.7"


def test_client_ip_trusted_peer_without_cf_header_uses_peer(trusted_gateway):
    from core.rate_limit import get_client_ip

    assert get_client_ip(_request(DOCKER_GATEWAY)) == DOCKER_GATEWAY  # pedido directo / testes


def test_client_ip_ignores_headers_when_trust_proxy_off(monkeypatch):
    from core.rate_limit import get_client_ip

    monkeypatch.delenv("TRUST_PROXY", raising=False)
    monkeypatch.setenv("TRUSTED_PROXY_IPS", DOCKER_GATEWAY)
    request = _request(DOCKER_GATEWAY, {"CF-Connecting-IP": "203.0.113.9"})
    assert get_client_ip(request) == DOCKER_GATEWAY


def test_forged_xff_cannot_open_admin_local_only(trusted_gateway, monkeypatch):
    """O gate de loopback do admin lê o par TCP, nunca cabeçalhos (core/local_only.py)."""
    from core.config import get_settings
    from core.local_only import admin_must_be_local

    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.delenv("DIOMIKA_BETA", raising=False)
    monkeypatch.delenv("DIOMIKA_DESKTOP_GATE", raising=False)
    get_settings.cache_clear()
    try:
        request = _request(DOCKER_GATEWAY, {"X-Forwarded-For": "127.0.0.1", "CF-Connecting-IP": "127.0.0.1"})
        with pytest.raises(HTTPException) as exc:
            admin_must_be_local(request)
        assert exc.value.status_code == 403
    finally:
        get_settings.cache_clear()


# --- Limite dos formulários: depois do Turnstile e por IP real --------------

_FORMS = {
    "contacto": (
        "/contacto",
        "routes.contact.run_contact_submission_saga",
        SimpleNamespace(email_sent=True, status="Nova"),
        {
            "nome": "Ana Silva",
            "email": "ana@example.com",
            "contacto": "912345678",
            "assunto": "Pedido",
            "mensagem": "Gostaria de pedir um orçamento.",
        },
    ),
    "orcamento": (
        "/orcamentos",
        "routes.orcamentos.run_orcamento_submission_saga",
        SimpleNamespace(pedido_id="p1", status="Nova"),
        {
            "nome": "Ana Silva",
            "email": "ana@example.com",
            "linhas": [{"ean": "1234567890123", "numero_cor": 1, "quantidade": 1}],
        },
    ),
}


class _FakeTurnstile:
    """Substitui a verificação (sem rede) e regista o IP que recebe como remoteip."""

    def __init__(self):
        self.ok = True
        self.ips: list[str | None] = []

    def __call__(self, token, remote_ip=None):
        self.ips.append(remote_ip)
        if not self.ok:
            raise ValueError("Verificação anti-spam inválida")


@pytest.fixture(params=sorted(_FORMS))
def form(request, monkeypatch, trusted_gateway):
    """App completa, par de confiança 172.18.0.1; Turnstile, saga e BD substituídos."""
    from fastapi.testclient import TestClient

    import main
    from core import rate_limit
    from core.config import get_settings

    url, saga, saga_result, payload = _FORMS[request.param]
    monkeypatch.setenv("DIOMIKA_ENV", "development")
    monkeypatch.delenv("DIOMIKA_BETA", raising=False)
    get_settings.cache_clear()
    monkeypatch.setattr(rate_limit, "_hits", defaultdict(list))
    turnstile = _FakeTurnstile()
    monkeypatch.setattr("utils.turnstile.verify_turnstile", turnstile)
    monkeypatch.setattr(saga, AsyncMock(return_value=saga_result))
    monkeypatch.setattr("routes.orcamentos.validate_order_lines", lambda linhas: None)
    client = TestClient(main.app, base_url="http://localhost", client=(DOCKER_GATEWAY, 50000))

    def post(visitor_ip: str, idempotency_key: str | None = None):
        headers = {"CF-Connecting-IP": visitor_ip}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return client.post(url, json=payload, headers=headers)

    yield SimpleNamespace(post=post, turnstile=turnstile)
    get_settings.cache_clear()


def test_form_rate_limit_not_consumed_when_turnstile_fails(form):
    form.turnstile.ok = False
    for _ in range(8):  # o limite são 5 por minuto
        assert form.post("203.0.113.9").status_code == 400  # recusado pelo Turnstile, nunca 429

    form.turnstile.ok = True
    assert form.post("203.0.113.9").status_code == 200  # o limite do IP está intacto


def test_form_rate_limit_is_per_real_ip_and_applies_after_turnstile(form):
    for _ in range(5):
        assert form.post("203.0.113.9").status_code == 200
    assert form.post("203.0.113.9").status_code == 429  # o limite continua a valer depois do Turnstile
    assert form.post("203.0.113.10").status_code == 200  # outro visitante não é afectado
    assert form.turnstile.ips[-1] == "203.0.113.10"  # e o Turnstile recebe o IP real como remoteip


@pytest.mark.parametrize("form", ["contacto"], indirect=True)
def test_contact_rate_limit_never_reserves_idempotency_key(form, monkeypatch):
    """A chave só é reservada depois do Turnstile e do limite (API-07): um 429 não a deixa presa nem precisa de a libertar."""
    abort = Mock()
    begin = Mock(return_value="proceed")
    monkeypatch.setattr("routes.contact.get_cached_response", lambda key, op: None)
    monkeypatch.setattr("routes.contact.begin_idempotent_request", begin)
    monkeypatch.setattr("routes.contact.complete_idempotent_request", lambda key, op, payload: None)
    monkeypatch.setattr("routes.contact.abort_idempotent_request", abort)

    for _ in range(5):
        assert form.post("203.0.113.9", "chave-1").status_code == 200
    abort.assert_not_called()
    assert begin.call_count == 5
    assert form.post("203.0.113.9", "chave-1").status_code == 429
    assert begin.call_count == 5  # o 6.º pedido nem chegou à chave
