"""Sessões curtas HMAC para o backoffice — Redis se disponível, senão memória.

Uma sessão activa por utilizador; idle timeout + TTL absoluto; multi-worker via Redis.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from typing import Any

logger = logging.getLogger("diomika-api")

# Máximo 7 dias e 12 h sem uso (antes: 30 dias, sem limite de inactividade). "0" desliga o idle.
SESSION_TTL_SECONDS = int(os.getenv("ADMIN_SESSION_TTL_MINUTES") or "10080") * 60
SESSION_IDLE_SECONDS = int((os.getenv("ADMIN_SESSION_IDLE_MINUTES") or "720").strip()) * 60
_PREFIX = "dms1."
_revoked: set[str] = set()
_active_jti: dict[str, str] = {}
_last_seen: dict[str, int] = {}  # jti -> unix ts
_lock = threading.Lock()


def _secret() -> bytes:
    # Fonte única: API_SECRET_KEY (sem alias ADMIN_SESSION_SECRET — menos superfície)
    raw = (os.getenv("API_SECRET_KEY") or "").strip()
    if not raw or len(raw) < 32:
        raise RuntimeError("API_SECRET_KEY (>=32 chars) obrigatório para sessões admin")
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _redis_required() -> bool:
    from core.config import get_settings

    s = get_settings()
    return bool(s.is_production and not s.is_beta)


def _redis():
    try:
        from core.redis_client import get_redis

        return get_redis()
    except Exception:
        return None


def _ensure_redis_for_issue() -> None:
    """Login em produção final exige Redis; devolve 503 em vez de 500/Sentry noise."""
    if not _redis_required():
        return
    if _redis() is not None:
        return
    from fastapi import HTTPException

    raise HTTPException(
        status_code=503,
        detail="Sessões admin indisponíveis — Redis em falta (REDIS_URL / contentor redis).",
    )


def _redis_set_active(username: str, jti: str, ttl: int) -> None:
    client = _redis()
    if client is None:
        return
    key = username.strip().lower()
    try:
        old = client.get(f"diomika:sess:user:{key}")
        if old and old != jti:
            client.setex(f"diomika:sess:revoked:{old}", ttl + 60, "1")
        pipe = client.pipeline()
        pipe.setex(f"diomika:sess:user:{key}", ttl, jti)
        pipe.setex(f"diomika:sess:seen:{jti}", ttl, str(int(time.time())))
        pipe.execute()
    except Exception as exc:
        logger.debug("Redis session set falhou: %s", exc)


def _redis_revoke(username: str, jti: str) -> None:
    client = _redis()
    if client is None:
        return
    key = username.strip().lower()
    try:
        pipe = client.pipeline()
        pipe.setex(f"diomika:sess:revoked:{jti}", SESSION_TTL_SECONDS + 60, "1")
        pipe.delete(f"diomika:sess:seen:{jti}")
        cur = client.get(f"diomika:sess:user:{key}")
        if cur == jti:
            pipe.delete(f"diomika:sess:user:{key}")
        pipe.execute()
    except Exception as exc:
        logger.debug("Redis session revoke falhou: %s", exc)


def _redis_revoke_user(username: str) -> None:
    client = _redis()
    if client is None:
        return
    key = username.strip().lower()
    try:
        jti = client.get(f"diomika:sess:user:{key}")
        if jti:
            client.setex(f"diomika:sess:revoked:{jti}", SESSION_TTL_SECONDS + 60, "1")
            client.delete(f"diomika:sess:seen:{jti}")
        client.delete(f"diomika:sess:user:{key}")
    except Exception as exc:
        logger.debug("Redis session revoke_user falhou: %s", exc)


def _redis_session_ok(username: str, jti: str, *, touch: bool) -> bool | None:
    """True/False se Redis OK; None se indisponível (usar memória)."""
    client = _redis()
    if client is None:
        return None
    key = username.strip().lower()
    try:
        if client.get(f"diomika:sess:revoked:{jti}"):
            return False
        active = client.get(f"diomika:sess:user:{key}")
        if active is None or active != jti:
            return False
        seen_raw = client.get(f"diomika:sess:seen:{jti}")
        now = int(time.time())
        if seen_raw:
            try:
                last = int(seen_raw)
            except ValueError:
                last = now
            if SESSION_IDLE_SECONDS > 0 and now - last > SESSION_IDLE_SECONDS:
                _redis_revoke(username, jti)
                return False
        if touch:
            client.setex(f"diomika:sess:seen:{jti}", SESSION_TTL_SECONDS, str(now))
        return True
    except Exception as exc:
        logger.debug("Redis session check falhou: %s", exc)
        return None


def issue_session(*, username: str, role: str) -> tuple[str, int]:
    """Emite token e invalida sessões anteriores do mesmo utilizador."""
    # Validar secret antes de Redis — testes e erros de config mais claros
    _secret()
    _ensure_redis_for_issue()
    now = int(time.time())
    jti = secrets.token_hex(8)
    payload = {
        "u": username,
        "r": role,
        "iat": now,
        "exp": now + SESSION_TTL_SECONDS,
        "jti": jti,
    }
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64url(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    key = username.strip().lower()
    with _lock:
        old = _active_jti.get(key)
        if old and old != jti:
            _revoked.add(old)
            _last_seen.pop(old, None)
        _active_jti[key] = jti
        _last_seen[jti] = now
        if len(_revoked) > 5000:
            _revoked.clear()
    _redis_set_active(username, jti, SESSION_TTL_SECONDS)
    return f"{_PREFIX}{body}.{sig}", SESSION_TTL_SECONDS


def revoke_session(token: str) -> None:
    parsed = parse_session(token, check_exp=False, touch=False)
    if not parsed:
        return
    jti = str(parsed.get("jti") or "")
    user = str(parsed.get("username") or "").strip().lower()
    if not jti:
        return
    with _lock:
        _revoked.add(jti)
        _last_seen.pop(jti, None)
        if user and _active_jti.get(user) == jti:
            _active_jti.pop(user, None)
        if len(_revoked) > 5000:
            _revoked.clear()
    if user:
        _redis_revoke(user, jti)


def revoke_all_for_user(username: str) -> None:
    key = (username or "").strip().lower()
    if not key:
        return
    with _lock:
        jti = _active_jti.pop(key, None)
        if jti:
            _revoked.add(jti)
            _last_seen.pop(jti, None)
    _redis_revoke_user(key)


def parse_session(
    token: str | None,
    *,
    check_exp: bool = True,
    touch: bool = True,
) -> dict[str, Any] | None:
    if not token or not token.startswith(_PREFIX):
        return None
    raw = token[len(_PREFIX) :]
    try:
        body, sig = raw.rsplit(".", 1)
    except ValueError:
        return None
    expected = _b64url(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(_b64url_decode(body))
    except Exception:
        return None
    jti = str(payload.get("jti") or "")
    username = str(payload.get("u") or "").strip()
    role = str(payload.get("r") or "").strip()
    if not username or not role:
        return None

    # Produção final sem Redis: fail-closed (sessão inválida), sem RuntimeError.
    if _redis_required() and _redis() is None:
        return None

    redis_ok = _redis_session_ok(username, jti, touch=touch)
    if redis_ok is False:
        return None
    if redis_ok is None:
        with _lock:
            if jti and jti in _revoked:
                return None
            key = username.lower()
            active = _active_jti.get(key)
            if active is None or jti != active:
                return None
            now = int(time.time())
            last = _last_seen.get(jti, now)
            if SESSION_IDLE_SECONDS > 0 and now - last > SESSION_IDLE_SECONDS:
                _revoked.add(jti)
                _active_jti.pop(key, None)
                _last_seen.pop(jti, None)
                return None
            if touch:
                _last_seen[jti] = now

    if check_exp and int(payload.get("exp") or 0) < int(time.time()):
        return None
    return {"username": username, "role": role, "jti": jti, "exp": payload.get("exp")}


def is_session_token(token: str | None) -> bool:
    return bool(token and token.startswith(_PREFIX))
