"""Middleware: segurança, request-id, rate limit global."""
from __future__ import annotations

import os
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core import metrics
from core.config import get_settings
from core.rate_limit import check_global_rate_limit
from core.path_patterns import is_public_catalog_path

ALLOWED_CORS_HEADERS = [
    "Accept",
    "Accept-Language",
    "Content-Language",
    "Content-Type",
    "Authorization",
    "X-API-Key",
    "Idempotency-Key",
    "X-Request-Id",
]

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response: Response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        route = request.scope.get("route")
        metrics.observe(
            request.method,
            getattr(route, "path", "unmatched"),
            response.status_code,
            time.perf_counter() - started,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        if get_settings().is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response


class CatalogCacheHeadersMiddleware(BaseHTTPMiddleware):
    """Cache-Control para leituras públicas de catálogo."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        if request.method != "GET" or response.status_code != 200:
            return response
        path = request.url.path
        # Sem cache no browser: com max-age=300 + stale-while-revalidate=600 o
        # browser mostrava o catálogo antigo até 15 min depois de publicar. A
        # velocidade vem da cache na Cloudflare (functions/api na loja), que é
        # invalidada pela versão do catálogo.
        if is_public_catalog_path(path):
            response.headers.setdefault("Cache-Control", "no-cache")
        return response


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit tiered — catálogo 600/min, global 120/min, admin 300/min (loopback isento)."""

    async def dispatch(self, request: Request, call_next):
        blocked = check_global_rate_limit(request)
        if blocked is not None:
            return blocked
        return await call_next(request)


class LatencyAlertMiddleware(BaseHTTPMiddleware):
    """Alerta se request demorar mais que ALERT_LATENCY_MS (default 2000 — sempre on)."""

    def __init__(self, app):
        super().__init__(app)
        try:
            self.threshold_ms = max(0, int(os.getenv("ALERT_LATENCY_MS") or "2000"))
        except ValueError:
            self.threshold_ms = 2000

    async def dispatch(self, request: Request, call_next):
        if self.threshold_ms <= 0:
            return await call_next(request)
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if elapsed_ms >= self.threshold_ms and not request.url.path.startswith(("/health", "/system/desktop-updates")):
            try:
                from core.alerts import send_alert

                send_alert(
                    "Latência elevada",
                    severity="warning",
                    detail={
                        "path": request.url.path,
                        "method": request.method,
                        "ms": int(elapsed_ms),
                        "threshold_ms": self.threshold_ms,
                        "request_id": getattr(request.state, "request_id", None),
                    },
                )
            except Exception:
                pass
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejeita bodies demasiado grandes (DoS) via Content-Length.

    Não consumir request.stream() aqui: BaseHTTPMiddleware + re-inject
    do body parte o parsing JSON (login/admin POST → 422 body missing).
    """

    MAX_BYTES = int(__import__("os").getenv("MAX_REQUEST_BODY_BYTES") or str(2 * 1024 * 1024))

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl:
            try:
                if int(cl) > self.MAX_BYTES:
                    return Response("Payload demasiado grande", status_code=413)
            except ValueError:
                return Response("Content-Length inválido", status_code=400)
        return await call_next(request)


class BotDefenseMiddleware(BaseHTTPMiddleware):
    """Bloqueia bots agressivos conhecidos por User-Agent."""

    async def dispatch(self, request: Request, call_next):
        from core.bot_defense import is_bot_user_agent, log_bot_attempt

        user_agent = request.headers.get("user-agent", "")
        if is_bot_user_agent(user_agent):
            client_ip = request.client.host if request.client else "unknown"
            log_bot_attempt(client_ip, user_agent, request.url.path)
            return Response("Acesso negado", status_code=403)

        return await call_next(request)
