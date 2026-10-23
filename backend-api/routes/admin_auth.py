"""Login local do backoffice — username/password + sessão curta."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.admin_users import (
    authenticate,
    begin_mfa_setup,
    change_password,
    confirm_mfa_setup,
    ensure_bootstrap,
    get_user,
    has_users,
    mfa_required_globally,
    set_user_disabled,
    verify_password,
)
from core.alerts import send_alert
from core.audit import log_admin_action
from core.auth import Role, require_admin, require_api_key
from core.local_only import admin_must_be_local
from core.rate_limit import get_client_ip, rate_limit, rate_limit_absolute
from core.session_tokens import SESSION_TTL_SECONDS, issue_session, revoke_session

router = APIRouter(
    prefix="/admin/auth",
    tags=["Admin Auth"],
    dependencies=[Depends(admin_must_be_local)],
)


class LoginBody(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    totp_code: str | None = Field(default=None, max_length=12)


class MfaConfirmBody(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    totp_code: str = Field(min_length=6, max_length=12)


class DisableUserBody(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    disabled: bool = True


class ChangePasswordBody(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


@router.get("/status")
def auth_status():
    ensure_bootstrap()
    return {
        "login_required": has_users(),
        "session_ttl_seconds": SESSION_TTL_SECONDS,
        "admin_local_only": False,
        "desktop_gate_required": True,
        "mfa_required": mfa_required_globally(),
    }


@router.post("/login")
def login(body: LoginBody, request: Request):
    ensure_bootstrap()
    if not has_users():
        raise HTTPException(
            status_code=503,
            detail="Login não configurado — defina ADMIN_BOOTSTRAP_USER e ADMIN_BOOTSTRAP_PASSWORD.",
        )

    # Login: limitar por IP + por username (anti brute-force multi-IP)
    rate_limit(request, "admin_login", max_calls=5, window_seconds=60)  # 5/min por IP (Redis)
    user_key = (body.username or "").strip().lower()[:64] or "unknown"
    rate_limit_absolute(f"admin_login_user:{user_key}", max_calls=10, window_seconds=300)
    ip = get_client_ip(request)

    user, err = authenticate(body.username, body.password, totp_code=body.totp_code)
    if err == "mfa_required":
        return {"mfa_required": True, "detail": "Introduza o código TOTP da app autenticadora."}
    if err == "mfa_setup_required":
        return {
            "mfa_setup_required": True,
            "detail": "ADMIN_MFA_REQUIRED=1 — configure MFA via POST /admin/auth/mfa/setup",
        }
    if err or not user:
        # Resposta genérica ao cliente — sem enumeração (lockout/disabled/tentativas).
        log_admin_action(
            action="login_failed",
            resource="auth",
            role="anonymous",
            actor=body.username[:64],
            client_ip=ip,
            request_id=getattr(request.state, "request_id", None),
            detail={"reason": err or "invalid"},
        )
        send_alert(
            "Admin login falhou",
            severity="warning",
            detail={"username": body.username[:64], "ip": ip, "reason": err or "invalid"},
        )
        try:
            from core.anomaly import note_login_failure

            note_login_failure(body.username[:64], ip)
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token, ttl = issue_session(username=user["username"], role=user["role"])
    log_admin_action(
        action="login_ok",
        resource="auth",
        role=user["role"],
        actor=user["username"],
        client_ip=ip,
        request_id=getattr(request.state, "request_id", None),
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ttl,
        "username": user["username"],
        "role": user["role"],
        "mfa_enabled": bool(user.get("mfa_enabled")),
    }


@router.post("/mfa/setup")
def mfa_setup(body: LoginBody, request: Request):
    """Inicia enrolamento TOTP (password correcta; código ainda não activo)."""
    ensure_bootstrap()
    rate_limit(request, "admin_mfa_setup", max_calls=10, window_seconds=300)
    raw = get_user(body.username)
    if not raw or not verify_password(body.password, str(raw.get("password_hash") or "")):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    if raw.get("totp_secret"):
        raise HTTPException(status_code=400, detail="MFA já activo nesta conta")
    try:
        return begin_mfa_setup(body.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/mfa/confirm")
def mfa_confirm(body: MfaConfirmBody, request: Request):
    ensure_bootstrap()
    rate_limit(request, "admin_mfa_confirm", max_calls=20, window_seconds=300)
    raw = get_user(body.username)
    if not raw or not verify_password(body.password, str(raw.get("password_hash") or "")):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    try:
        confirm_mfa_setup(body.username, body.totp_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_admin_action(
        action="mfa_enabled",
        resource="auth",
        role=str(raw.get("role") or "admin"),
        actor=body.username,
        client_ip=get_client_ip(request),
        request_id=getattr(request.state, "request_id", None),
    )
    return {"ok": True, "mfa_enabled": True}


@router.post("/logout")
def logout(request: Request, role: Role = Depends(require_api_key)):
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        revoke_session(auth.split(" ", 1)[1].strip())
    log_admin_action(
        action="logout",
        resource="auth",
        role=str(role),
        actor=getattr(request.state, "api_actor", None),
        client_ip=get_client_ip(request),
        request_id=getattr(request.state, "request_id", None),
    )
    return {"ok": True}


@router.get("/me")
def me(request: Request, role: Role = Depends(require_api_key)):
    return {
        "username": getattr(request.state, "api_actor", "unknown"),
        "role": role,
    }


@router.post("/users/disable")
def disable_user(
    body: DisableUserBody,
    request: Request,
    role: Role = Depends(require_admin),
):
    """Desactiva/reactiva user local e revoga sessões (só role admin)."""
    if role != "admin":
        raise HTTPException(status_code=403, detail="Só admin pode desactivar utilizadores")
    actor = str(getattr(request.state, "api_actor", "") or "")
    if actor.strip().lower() == body.username.strip().lower() and body.disabled:
        raise HTTPException(status_code=400, detail="Não pode desactivar a própria conta activa")
    try:
        set_user_disabled(body.username, body.disabled)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    log_admin_action(
        action="user_disabled" if body.disabled else "user_enabled",
        resource="auth",
        role=str(role),
        actor=actor,
        client_ip=get_client_ip(request),
        request_id=getattr(request.state, "request_id", None),
        detail={"username": body.username, "disabled": body.disabled},
    )
    return {"ok": True, "username": body.username, "disabled": body.disabled}


@router.post("/change-password")
def change_own_password(
    body: ChangePasswordBody,
    request: Request,
    role: Role = Depends(require_api_key),
):
    """Altera password do actor autenticado e revoga todas as sessões."""
    actor = str(getattr(request.state, "api_actor", "") or "").strip()
    if not actor or actor in ("api-key", "dev-open"):
        raise HTTPException(status_code=400, detail="Change-password só para sessão de utilizador")
    try:
        change_password(actor, body.current_password, body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_admin_action(
        action="password_changed",
        resource="auth",
        role=str(role),
        actor=actor,
        client_ip=get_client_ip(request),
        request_id=getattr(request.state, "request_id", None),
    )
    send_alert(
        "Admin password alterada",
        severity="warning",
        detail={"username": actor},
    )
    return {"ok": True, "relogin_required": True}
