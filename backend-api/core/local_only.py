"""Admin/system: loopback OU app desktop com gate partilhado (não API aberta)."""
from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request

from core.config import get_settings

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})
_DESKTOP_HEADER = "x-diomika-desktop"


def peer_is_loopback(request: Request) -> bool:
    """IP do peer TCP — não usar X-Forwarded-For (fácil de forjar)."""
    if request.client and request.client.host:
        peer = request.client.host.strip().lower()
        return peer in _LOOPBACK or peer.startswith("127.")
    return False


def desktop_gate_secret() -> str:
    return (os.getenv("DIOMIKA_DESKTOP_GATE") or "").strip()


def desktop_gate_ok(request: Request) -> bool:
    """Backoffice Electron envia X-Diomika-Desktop = DIOMIKA_DESKTOP_GATE."""
    expected = desktop_gate_secret()
    if not expected:
        return False
    got = (request.headers.get(_DESKTOP_HEADER) or "").strip()
    if not got:
        return False
    return hmac.compare_digest(got, expected)


def privileged_access_ok(request: Request) -> bool:
    """Loopback (ops na VM) ou app desktop com gate válido.

    Em dev e em beta, este gate de rede fica desligado de propósito — em
    beta ainda não há domínio/VM fixos, por isso o admin precisa de ser
    acessível de fora do loopback. Isso significa que, nesses modos, a
    única barreira real contra um admin exposto publicamente é a
    autenticação (password + MFA) em core/admin_users.py — por isso
    mfa_required_globally() exige MFA em beta tal como em produção final,
    não só nesta última. Se o teu "beta" for mesmo um link privado que só
    tu conheces (não divulgado, DNS não público), o risco é baixo; se for
    um soft-launch já acessível ao público, considera manter esta função
    tão restritiva como em produção final (tirar o `settings.is_beta` da
    condição abaixo) e usar antes um túnel/VPN para administração remota.
    """
    settings = get_settings()
    if not settings.is_production or settings.is_beta:
        return True
    if peer_is_loopback(request):
        return True
    return desktop_gate_ok(request)


def admin_must_be_local(request: Request) -> None:
    """Produção final: só loopback ou backoffice desktop (header gate)."""
    if privileged_access_ok(request):
        return
    raise HTTPException(
        status_code=403,
        detail="Admin/system só via backoffice Diomika ou localhost.",
    )
