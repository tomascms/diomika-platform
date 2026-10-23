"""HTTP helpers para scripts de deploy/teste — TLS separado da API.

NUNCA define DIOMIKA_SSL_INSECURE (isso afectaria a API).
Para CLI contra trycloudflare/pages com CA local partida:
  DEPLOY_TLS_INSECURE=1
"""
from __future__ import annotations

import os
import ssl
from pathlib import Path

try:
    import certifi
except ImportError:
    certifi = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]


def load_test_env() -> None:
    """Carrega .env sem activar SSL insecure na API."""
    dotenv = ROOT / ".env"
    if dotenv.is_file():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def deploy_tls_insecure_allowed() -> bool:
    return (os.getenv("DEPLOY_TLS_INSECURE") or "").strip().lower() in ("1", "true", "yes")


def ssl_context() -> ssl.SSLContext:
    """Contexto TLS para urllib nos scripts deploy/ — default: certifi."""
    if deploy_tls_insecure_allowed():
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    if certifi:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()
