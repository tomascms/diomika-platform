"""Testes rotas públicas meta (/, robots, security.txt)."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.diomika.com,testserver")
    from main import app

    return TestClient(app, base_url="https://api.diomika.com")


def test_api_root(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "diomika-api"
    assert body["health"] == "/health"
    assert "status" in body


def test_robots_txt(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "Disallow: /" in r.text


def test_security_txt(client):
    r = client.get("/.well-known/security.txt")
    assert r.status_code == 200
    assert "Contact:" in r.text


def test_metrics_not_public_and_counts_requests(client, monkeypatch):
    from core.config import get_settings
    from core.metrics import render

    client.get("/health/live")
    assert 'route="/health/live",code="2xx"}' in render()
    # Com chave configurada (como em produção) /metrics exige-a; sem isto o teste dependia do .env local.
    monkeypatch.setenv("API_SECRET_KEY", "k" * 40)
    get_settings.cache_clear()
    try:
        assert client.get("/metrics").status_code in (401, 403, 404)
    finally:
        get_settings.cache_clear()
