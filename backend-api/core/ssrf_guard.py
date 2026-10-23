"""SSRF defense — allow-list de hosts para qualquer fetch URL futuro."""
from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlparse


class UnsafeUrlError(ValueError):
    pass


def _blocked_networks() -> list[ipaddress._BaseNetwork]:
    nets = [
        "0.0.0.0/8",
        "10.0.0.0/8",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    ]
    return [ipaddress.ip_network(n) for n in nets]


def allowed_fetch_hosts() -> set[str]:
    raw = (os.getenv("SSRF_ALLOW_HOSTS") or "").strip()
    hosts = {h.strip().lower() for h in raw.split(",") if h.strip()}
    # Defaults seguros do stack Diomika + webhooks de alerta comuns
    hosts.update(
        {
            "api.cloudflare.com",
            "challenges.cloudflare.com",
            "hooks.slack.com",
            "discord.com",
            "discordapp.com",
            "api.axiom.co",
            "eu-central-1.aws.edge.axiom.co",
            "us-east-1.aws.edge.axiom.co",
            "ntfy.sh",
        }
    )
    return hosts


def assert_safe_outbound_url(url: str) -> str:
    """Rejeita URLs para loopback/RFC1918/metadata e hosts fora da allow-list."""
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in ("https",):
        raise UnsafeUrlError("Apenas https permitido")
    host = (parsed.hostname or "").lower()
    if not host:
        raise UnsafeUrlError("Host em falta")
    if host not in allowed_fetch_hosts():
        raise UnsafeUrlError(f"Host não permitido: {host}")
    try:
        ip = ipaddress.ip_address(host)
        for net in _blocked_networks():
            if ip in net:
                raise UnsafeUrlError("IP privado/bloqueado")
    except ValueError:
        pass  # hostname não é IP literal — OK se na allow-list
    return url
