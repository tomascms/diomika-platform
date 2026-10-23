"""Middleware de fronteira — /admin e /system nunca ficam abertos sem gate."""
from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.config import get_settings
from core.local_only import privileged_access_ok

_PRIVILEGED_PREFIXES = ("/admin", "/system", "/health/detail")
_PUBLIC_MUTATE_PREFIXES = ("/contacto", "/orcamentos")


def lockdown_active() -> bool:
    return (os.getenv("SECURITY_LOCKDOWN") or "").strip().lower() in ("1", "true", "yes")


class PrivilegedPathMiddleware(BaseHTTPMiddleware):
    """Fail-closed para caminhos privilegiados + lockdown global."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        settings = get_settings()

        if lockdown_active():
            if path in ("/health", "/health/ready") and request.method == "GET":
                return await call_next(request)
            if path.startswith(_PRIVILEGED_PREFIXES) or any(
                path.startswith(p) for p in _PUBLIC_MUTATE_PREFIXES
            ):
                return JSONResponse(
                    status_code=503,
                    content={"detail": "SECURITY_LOCKDOWN activo — operações suspensas."},
                )

        if settings.is_production and not settings.is_beta:
            if any(path.startswith(p) for p in _PRIVILEGED_PREFIXES):
                if not privileged_access_ok(request):
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": "Admin/system só via backoffice Diomika ou localhost."
                        },
                    )

        return await call_next(request)
