"""Cliente Supabase — TLS com certifi por defeito; verify=False nunca é auto-activado."""
from __future__ import annotations

import logging
import os
import ssl
import sys

import certifi
import httpx
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from core.env_loader import load_project_env

load_project_env()

logger = logging.getLogger("diomika-api")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

_env = (os.getenv("DIOMIKA_ENV") or "development").strip().lower()
_is_production = _env == "production"
_is_beta = (os.getenv("DIOMIKA_BETA") or "").strip().lower() in ("1", "true", "yes")
_ssl_flag = (os.getenv("DIOMIKA_SSL_INSECURE") or "").strip().lower() in ("1", "true", "yes")

# Nunca default por beta. Só flag explícita, e nunca em produção final.
_is_final_production = _is_production and not _is_beta
if _ssl_flag and _is_final_production:
    print(
        "ERRO: DIOMIKA_SSL_INSECURE=1 em producao final — abortar.\n"
        "  Remova DIOMIKA_SSL_INSECURE do .env (API usa certifi).",
        file=sys.stderr,
    )
    sys.exit(1)

_ssl_insecure = _ssl_flag and not _is_final_production

_http_limits = httpx.Limits(max_connections=80, max_keepalive_connections=25, keepalive_expiry=30.0)
_http_timeout = httpx.Timeout(15.0, connect=3.0)


class _RetryTransport(httpx.BaseTransport):
    """Retry curto em falhas transitórias — só pedidos GET idempotentes."""

    def __init__(self, transport: httpx.BaseTransport, *, retries: int = 1):
        self._transport = transport
        self._retries = max(0, retries)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        import time

        last_exc: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                response = self._transport.handle_request(request)
                if (
                    request.method.upper() == "GET"
                    and response.status_code in (502, 503, 504)
                    and attempt < self._retries
                ):
                    time.sleep(0.15 * (attempt + 1))
                    continue
                return response
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                if request.method.upper() == "GET" and attempt < self._retries:
                    time.sleep(0.15 * (attempt + 1))
                    continue
                raise
        if last_exc:
            raise last_exc
        raise RuntimeError("Retry transport failed")


if _ssl_insecure:
    print(
        "AVISO: DIOMIKA_SSL_INSECURE=1 — TLS desactivado (flag explícita; nunca auto).\n"
        "  Remova antes do domain day / VM producao.",
        file=sys.stderr,
    )
    _base = httpx.HTTPTransport(verify=False, retries=0)
else:
    _ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    _base = httpx.HTTPTransport(verify=_ssl_ctx, retries=0)

_http = httpx.Client(
    transport=_RetryTransport(_base),
    timeout=_http_timeout,
    limits=_http_limits,
)

_options = SyncClientOptions(httpx_client=_http)
supabase: Client = create_client(url or "", key or "", options=_options)


def get_db() -> Client:
    return supabase
