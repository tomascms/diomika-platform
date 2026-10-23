"""Utilizadores locais do backoffice — ficheiro local, nunca no browser."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from paths import BACKEND_ROOT

logger = logging.getLogger("diomika-api")

_STORE = BACKEND_ROOT / "data" / "admin_users.json"
_LOCK = threading.Lock()


def _get_str(obj: dict, key: str, default: str = "") -> str:
    """Safe dict.get() for strings — always returns str, never None."""
    return str(obj.get(key) or default)

MAX_FAILED = int(os.getenv("ADMIN_LOGIN_MAX_FAILED") or "5")
LOCKOUT_MINUTES = int(os.getenv("ADMIN_LOGIN_LOCKOUT_MINUTES") or "15")

VALID_ROLES = frozenset({"admin", "ops", "catalog", "pedidos", "mensagens"})
MIN_PASSWORD_LEN = int(os.getenv("ADMIN_PASSWORD_MIN_LEN") or "12")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def validate_password_strength(password: str) -> None:
    """Política produção: 12+ chars, maiúscula, minúscula, dígito, símbolo."""
    pwd = password or ""
    if len(pwd) < MIN_PASSWORD_LEN:
        raise ValueError(f"password deve ter pelo menos {MIN_PASSWORD_LEN} caracteres")
    if not any(c.isupper() for c in pwd):
        raise ValueError("password deve incluir pelo menos uma maiúscula")
    if not any(c.islower() for c in pwd):
        raise ValueError("password deve incluir pelo menos uma minúscula")
    if not any(c.isdigit() for c in pwd):
        raise ValueError("password deve incluir pelo menos um dígito")
    if not any(not c.isalnum() for c in pwd):
        raise ValueError("password deve incluir pelo menos um símbolo")
    if pwd.lower() in {"password", "password123", "admin123456", "diomika12345", "diomika12345!"}:
        raise ValueError("password demasiado comum")


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, salt_b64, hash_b64 = encoded.split("$", 2)
        if algo != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def _empty() -> dict[str, Any]:
    return {"users": []}


def _load() -> dict[str, Any]:
    if not _STORE.is_file():
        return _empty()
    try:
        data = json.loads(_STORE.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("users"), list):
            return _empty()
        return data
    except Exception:
        return _empty()


def _save(data: dict[str, Any]) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    # Backup rotativo antes de escrever
    if _STORE.is_file():
        bak = _STORE.with_suffix(".json.bak")
        try:
            bak.write_bytes(_STORE.read_bytes())
        except Exception:
            logger.debug("backup admin_users falhou", exc_info=True)
    tmp = _STORE.with_suffix(".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(_STORE)
    try:
        if hasattr(os, "chmod"):
            os.chmod(_STORE, 0o600)
    except Exception:
        pass


def list_usernames() -> list[str]:
    with _LOCK:
        return [_get_str(u, "username") for u in _load().get("users", []) if u.get("username")]


def has_users() -> bool:
    return bool(list_usernames())


def get_user(username: str) -> dict[str, Any] | None:
    key = (username or "").strip().lower()
    with _LOCK:
        for u in _load().get("users", []):
            if _get_str(u, "username").lower() == key:
                return dict(u)
    return None


def upsert_user(username: str, password: str, role: str = "admin") -> None:
    username = (username or "").strip()
    role = (role or "admin").strip().lower()
    if not username or len(username) < 2:
        raise ValueError("username inválido")
    validate_password_strength(password)
    if role not in VALID_ROLES:
        raise ValueError(f"role inválido: {role}")
    with _LOCK:
        data = _load()
        users = data.setdefault("users", [])
        found = False
        for u in users:
            if _get_str(u, "username").lower() == username.lower():
                u["password_hash"] = hash_password(password)
                u["role"] = role
                u["failed_attempts"] = 0
                u["locked_until"] = None
                found = True
                break
        if not found:
            users.append(
                {
                    "username": username,
                    "password_hash": hash_password(password),
                    "role": role,
                    "failed_attempts": 0,
                    "locked_until": None,
                }
            )
        _save(data)
    # Password/role change invalida sessões activas deste utilizador
    try:
        from core.session_tokens import revoke_all_for_user

        revoke_all_for_user(username)
    except Exception:
        logger.exception("Falha a revogar sessões após upsert_user(%s)", username)


def _parse_locked(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def mfa_required_globally() -> bool:
    """MFA obrigatório por omissão em produção final E em beta (antes era
    preciso ADMIN_MFA_REQUIRED=1 explícito, e o modo beta ficava de fora —
    nesse modo o admin fica acessível remotamente (ver core/local_only.py)
    com só password a protegê-lo, o que tornava o MFA ainda mais necessário,
    não menos). ADMIN_MFA_REQUIRED=1 força em qualquer ambiente;
    ADMIN_MFA_REQUIRED=0 desliga mesmo em produção, se for mesmo essa a
    escolha."""
    raw = (os.getenv("ADMIN_MFA_REQUIRED") or "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False

    from core.config import get_settings

    return get_settings().is_production


def _totp_ok(secret: str, code: str) -> bool:
    try:
        import pyotp
    except ImportError as exc:
        raise RuntimeError("pyotp em falta — pip install pyotp") from exc
    totp = pyotp.TOTP(secret)
    return bool(totp.verify(code.strip(), valid_window=1))


def begin_mfa_setup(username: str) -> dict[str, str]:
    """Gera secret TOTP pendente (ainda não activo até confirm_mfa_setup)."""
    try:
        import pyotp
    except ImportError as exc:
        raise RuntimeError("pyotp em falta — pip install pyotp") from exc
    username = (username or "").strip()
    if not username:
        raise ValueError("username inválido")
    secret = pyotp.random_base32()
    with _LOCK:
        data = _load()
        for u in data.get("users", []):
            if _get_str(u, "username").lower() == username.lower():
                u["totp_secret_pending"] = secret
                _save(data)
                uri = pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="Diomika Admin")
                return {"secret": secret, "otpauth_uri": uri}
    raise ValueError("utilizador não encontrado")


def confirm_mfa_setup(username: str, code: str) -> None:
    username = (username or "").strip()
    with _LOCK:
        data = _load()
        for u in data.get("users", []):
            if _get_str(u, "username").lower() == username.lower():
                pending = _get_str(u, "totp_secret_pending")
                if not pending:
                    raise ValueError("sem setup MFA pendente")
                if not _totp_ok(pending, code):
                    raise ValueError("código MFA inválido")
                u["totp_secret"] = pending
                u.pop("totp_secret_pending", None)
                _save(data)
                return
    raise ValueError("utilizador não encontrado")


def authenticate(
    username: str,
    password: str,
    *,
    totp_code: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Devolve (user_public, erro). user_public sem hash."""
    username = (username or "").strip()
    if not username or not password:
        return None, "Credenciais inválidas"

    with _LOCK:
        data = _load()
        user = None
        idx = -1
        for i, u in enumerate(data.get("users", [])):
            if str(u.get("username") or "").lower() == username.lower():
                user = u
                idx = i
                break
        if user is None:
            return None, "Credenciais inválidas"

        if user.get("disabled"):
            return None, "Conta desactivada"

        locked_until = _parse_locked(user.get("locked_until"))
        now = _utcnow()
        if locked_until and locked_until > now:
            mins = max(1, int((locked_until - now).total_seconds() // 60) + 1)
            return None, f"Conta bloqueada. Tente dentro de ~{mins} min."

        if not verify_password(password, _get_str(user, "password_hash")):
            fails = int(user.get("failed_attempts") or 0) + 1
            user["failed_attempts"] = fails
            if fails >= MAX_FAILED:
                user["locked_until"] = (now + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
                user["failed_attempts"] = 0
                data["users"][idx] = user
                _save(data)
                return None, f"Demasiadas falhas. Conta bloqueada {LOCKOUT_MINUTES} min."
            data["users"][idx] = user
            _save(data)
            left = MAX_FAILED - fails
            return None, f"Credenciais inválidas ({left} tentativas restantes)"

        secret = _get_str(user, "totp_secret").strip()
        if mfa_required_globally():
            if secret:
                if not totp_code:
                    return None, "mfa_required"
                if not _totp_ok(secret, totp_code):
                    return None, "Código MFA inválido"
            else:
                return None, "mfa_setup_required"

        user["failed_attempts"] = 0
        user["locked_until"] = None
        data["users"][idx] = user
        _save(data)
        return {
            "username": _get_str(user, "username"),
            "role": _get_str(user, "role", "admin"),
            "mfa_enabled": bool(secret),
        }, None


def set_user_disabled(username: str, disabled: bool) -> None:
    """Desactiva/reactiva utilizador e revoga sessões se disabled=True."""
    key = (username or "").strip().lower()
    if not key:
        raise ValueError("username inválido")
    with _LOCK:
        data = _load()
        found = False
        for u in data.get("users", []):
            if _get_str(u, "username").lower() == key:
                u["disabled"] = bool(disabled)
                found = True
                break
        if not found:
            raise ValueError("utilizador não encontrado")
        _save(data)
    if disabled:
        try:
            from core.session_tokens import revoke_all_for_user

            revoke_all_for_user(username)
        except Exception:
            logger.exception("Falha a revogar sessões após disable(%s)", username)


def change_password(username: str, current_password: str, new_password: str) -> None:
    """Altera password (verifica actual) e revoga sessões."""
    user = get_user(username)
    if not user:
        raise ValueError("utilizador não encontrado")
    if not verify_password(current_password, _get_str(user, "password_hash")):
        raise ValueError("password actual incorrecta")
    validate_password_strength(new_password)
    upsert_user(username, new_password, role=_get_str(user, "role", "admin"))


def _bootstrap_credentials() -> tuple[str, str, str] | None:
    user = (os.getenv("ADMIN_BOOTSTRAP_USER") or "").strip()
    password = (os.getenv("ADMIN_BOOTSTRAP_PASSWORD") or "").strip()
    role = (os.getenv("ADMIN_BOOTSTRAP_ROLE") or "admin").strip().lower()
    if not user or not password:
        return None
    return user, password, role if role in VALID_ROLES else "admin"


def bootstrap_sync_enabled() -> bool:
    """Opt-in: alinhar password do user bootstrap com ADMIN_BOOTSTRAP_PASSWORD no arranque."""
    return (os.getenv("ADMIN_BOOTSTRAP_SYNC") or "").strip().lower() in ("1", "true", "yes")


def ensure_bootstrap() -> None:
    """Cria ou (opcionalmente) sincroniza utilizador inicial a partir de ADMIN_BOOTSTRAP_*."""
    creds = _bootstrap_credentials()
    if creds is None:
        if not has_users():
            logger.warning(
                "Sem utilizadores admin locais. Defina ADMIN_BOOTSTRAP_USER + "
                f"ADMIN_BOOTSTRAP_PASSWORD (min {MIN_PASSWORD_LEN} chars, letra+dígito) "
                "para activar login real."
            )
        return

    user, password, role = creds

    if has_users():
        if not bootstrap_sync_enabled():
            return
        existing = get_user(user)
        if existing is None:
            return
        current_hash = str(existing.get("password_hash") or "")
        if verify_password(password, current_hash):
            return
        try:
            upsert_user(user, password, role=str(existing.get("role") or role))
            logger.info(
                "Password bootstrap sincronizada para %s (ADMIN_BOOTSTRAP_SYNC=1)",
                user,
            )
        except ValueError as exc:
            logger.error("Sync bootstrap admin falhou: %s", exc)
        return

    try:
        upsert_user(user, password, role=role)
        logger.info("Utilizador bootstrap criado: %s (role=%s)", user, role)
    except ValueError as exc:
        logger.error("Bootstrap admin falhou: %s", exc)
