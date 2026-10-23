"""A pilha de middleware completa responde — e o filtro de bots não apanha
clientes legítimos.

Antes, RateLimitingMiddleware/HealthCheckMiddleware não eram ASGI válido e o
BotDefenseMiddleware recusava o healthcheck do Docker (User-Agent "curl") e o
UptimeRobot ("obot" dentro de "UptimeRobot").
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from core.bot_defense import is_bot_user_agent


@pytest.fixture(scope="module")
def client():
    import main

    # Sem `with`: não corre o lifespan (warm-up de cache / workers).
    # localhost é aceite pelo TrustedHostMiddleware em dev e em produção.
    return TestClient(main.app, base_url="http://localhost")


BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0 Safari/537.36"
)


def test_health_live_through_full_stack(client):
    resp = client.get("/health/live", headers={"User-Agent": BROWSER_UA})
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}
    assert resp.headers.get("x-request-id")
    assert resp.headers.get("x-ratelimit-tier") == "human"


def test_docker_healthcheck_user_agent_is_not_a_bot(client):
    resp = client.get("/health/live", headers={"User-Agent": "DiomikaHealthcheck/1.0"})
    assert resp.status_code == 200


def test_uptime_robot_is_allowed(client):
    ua = "Mozilla/5.0+(compatible; UptimeRobot/2.0; http://www.uptimerobot.com/)"
    assert is_bot_user_agent(ua) is False
    assert client.get("/health/live", headers={"User-Agent": ua}).status_code == 200


def test_scraper_is_blocked(client):
    resp = client.get("/health/live", headers={"User-Agent": "Scrapy/2.11 (+https://scrapy.org)"})
    assert resp.status_code == 403


@pytest.mark.parametrize(
    "ua",
    [
        "curl/8.5.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/141.0",
        "Mozilla/5.0 (compatible; DotBot/1.2)",
    ],
)
def test_blocked_patterns_still_match_at_token_start(ua):
    assert is_bot_user_agent(ua) is True


@pytest.mark.parametrize(
    "ua",
    [
        BROWSER_UA,
        "DiomikaBackoffice/1.0",
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    ],
)
def test_legit_clients_are_not_bots(ua):
    assert is_bot_user_agent(ua) is False
