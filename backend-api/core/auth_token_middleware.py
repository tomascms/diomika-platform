"""Middleware para autenticação admin com rotação automática de tokens."""
from __future__ import annotations

import logging
import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("diomika-api")

# Cache em memória de último token de cada user — evita renovação em cada request
_token_cache: dict[str, tuple[str, int]] = {}  # username -> (token, timestamp)
_cache_lock = __import__("threading").Lock()


class AdminTokenRotationMiddleware(BaseHTTPMiddleware):
    """
    Middleware de rotação automática de tokens admin.

    Se token é válido e está vencido (baseado em intervalo de rotação),
    emite novo token e devolve em header X-New-Session-Token.
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Apenas aplicar em rotas admin autenticadas
        if not request.url.path.startswith("/admin/"):
            return response

        if response.status_code not in (200, 201, 204):
            return response

        # Verificar se há token na requisição (Bearer)
        auth_header = request.headers.get("authorization", "").strip()
        if not auth_header.lower().startswith("bearer "):
            return response

        try:
            # Verificar se token merece rotação
            should_rotate = self._should_rotate_token(request)
            if should_rotate:
                new_token = self._issue_new_token(request)
                if new_token:
                    response.headers["X-New-Session-Token"] = new_token
                    response.headers["X-Token-Rotated"] = "true"
                    logger.debug("Token rotacionado (rotation middleware)")
        except Exception as exc:
            logger.debug(f"Token rotation middleware error: {exc}")

        return response

    def _should_rotate_token(self, request: Request) -> bool:
        """Verifica se token deve ser rotacionado."""
        from core.token_rotation import TOKEN_ROTATION_INTERVAL
        from core.session_tokens import parse_session, _PREFIX

        try:
            auth_header = request.headers.get("authorization", "").strip()
            if not auth_header.lower().startswith("bearer "):
                return False

            token = auth_header[7:]  # Remove "bearer "

            # Apenas processa tokens nossos
            if not token.startswith(_PREFIX):
                return False

            parsed = parse_session(token, check_exp=True, touch=False)
            if not parsed:
                return False

            username = parsed.get("username")
            if not username:
                return False

            # Verificar se está em cache (evita recalcular em cada request)
            with _cache_lock:
                if username in _token_cache:
                    _, last_check = _token_cache[username]
                    if time.time() - last_check < TOKEN_ROTATION_INTERVAL:
                        return False

            # Tokens com exp < 5 min devem ser rotacionados
            exp = parsed.get("exp", 0)
            now = int(time.time())
            return (exp - now) < TOKEN_ROTATION_INTERVAL
        except Exception:
            return False

    def _issue_new_token(self, request: Request) -> Optional[str]:
        """Emite novo token se current é válido."""
        from core.session_tokens import parse_session, issue_session, _PREFIX

        try:
            auth_header = request.headers.get("authorization", "").strip()
            if not auth_header.lower().startswith("bearer "):
                return None

            token = auth_header[7:]  # Remove "bearer "

            if not token.startswith(_PREFIX):
                return None

            parsed = parse_session(token, check_exp=True, touch=False)
            if not parsed:
                return None

            username = parsed.get("username")
            role = parsed.get("role")
            if not username or not role:
                return None

            # Emitir novo token
            new_token, ttl = issue_session(username=username, role=role)

            # Cache result para não emitir múltiplos tokens no mesmo intervalo
            with _cache_lock:
                _token_cache[username] = (new_token, int(time.time()))

            return new_token
        except Exception as exc:
            logger.debug(f"Failed to issue new token: {exc}")
            return None
