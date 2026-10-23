"""Verificação Cloudflare Turnstile."""
from __future__ import annotations

import asyncio
import os

import requests

from core.config import get_settings

try:
    import certifi

    _VERIFY = certifi.where()
except ImportError:
    _VERIFY = True

_TURNSTILE_TEST_SECRET = "1x0000000000000000000000000000000AA"
_TURNSTILE_DUMMY_TOKEN = "XXXX.DUMMY.TOKEN.XXXX"


def turnstile_enabled() -> bool:
    return bool((os.getenv("TURNSTILE_SECRET_KEY") or "").strip())


def _resolve_secret(settings) -> str:
    secret = (os.getenv("TURNSTILE_SECRET_KEY") or "").strip()
    if settings.is_beta and secret and not settings._turnstile_is_test_key():
        if (os.getenv("TURNSTILE_BETA_USE_TEST") or "1").strip().lower() in ("1", "true", "yes"):
            return _TURNSTILE_TEST_SECRET
    # Desenvolvimento local: frontend usa sitekey de teste em localhost
    if (
        not settings.is_production
        and not settings.is_beta
        and (os.getenv("TURNSTILE_DEV_USE_TEST") or "1").strip().lower() in ("1", "true", "yes")
    ):
        return _TURNSTILE_TEST_SECRET
    return secret


def verify_turnstile(token: str | None, remote_ip: str | None = None) -> None:
    """Levanta ValueError se verificação falhar."""
    settings = get_settings()
    secret = _resolve_secret(settings)

    if not secret:
        if settings.is_production:
            raise ValueError("Verificação anti-spam indisponível")
        return

    if not token:
        raise ValueError("Verificação anti-spam em falta")

    # Atalho beta (Pages / testes automatizados)
    if settings.is_beta and token == _TURNSTILE_DUMMY_TOKEN:
        return

    # Durante uma troca de widget (ex.: mudança de conta Cloudflare) a loja antiga e a
    # nova coexistem; a chave anterior continua aceite até ser removida do .env.
    previous = (os.getenv("TURNSTILE_SECRET_KEY_PREVIOUS") or "").strip()
    for candidate in [secret] + ([previous] if previous and previous != secret else []):
        if _siteverify(candidate, token, remote_ip):
            return
    raise ValueError("Verificação anti-spam inválida")


def _siteverify(secret: str, token: str, remote_ip: str | None) -> bool:
    payload = {"secret": secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        resp = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=payload,
            timeout=10,
            verify=_VERIFY,
        )
    except requests.RequestException as exc:
        raise ValueError("Verificação anti-spam indisponível") from exc

    return bool(resp.json().get("success"))


async def verify_turnstile_async(token: str | None, remote_ip: str | None = None) -> None:
    """Não bloqueia o event loop — usa thread para HTTP sync."""
    await asyncio.to_thread(verify_turnstile, token, remote_ip)
