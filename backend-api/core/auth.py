"""Autenticação API — chave máquina + sessão utilizador + ACL por role/tabela."""
from __future__ import annotations

import os
import secrets
from typing import Literal

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from core.config import get_settings
from core.session_tokens import is_session_token, parse_session

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

Role = Literal["admin", "ops", "catalog", "pedidos", "mensagens"]
BUSINESS_ROLES = frozenset({"admin", "ops", "catalog", "pedidos", "mensagens"})

# Infra — nunca no CRUD genérico
CRUD_INFRA_BLOCKED = frozenset({
    "admin_audit_log",
    "outbox_events",
    "saga_instances",
    "idempotency_keys",
    "message_history",
})

# Dados de negócio sensíveis — CRUD só com role dedicado (sem atalho “admin key = tudo”)
SENSITIVE_BUSINESS_TABLES = frozenset({
    "contact_messages",
    "pedidos_orcamento",
    "encomendas_internas",
})

SENSITIVE_TABLES = CRUD_INFRA_BLOCKED | SENSITIVE_BUSINESS_TABLES

Action = Literal["read", "create", "update", "delete", "upload", "hard_delete"]


def _key_roles() -> list[tuple[str, Role]]:
    """Chaves máquina por scope — admin/ops/catalog/pedidos/mensagens."""
    pairs: list[tuple[str, Role]] = []
    mapping: list[tuple[str, Role]] = [
        ("API_SECRET_KEY", "admin"),
        ("API_SECRET_KEY_PREVIOUS", "admin"),
        ("API_OPS_KEY", "ops"),
        ("API_CATALOG_KEY", "catalog"),
        ("API_PEDIDOS_KEY", "pedidos"),
        ("API_MENSAGENS_KEY", "mensagens"),
    ]
    for env_name, role in mapping:
        key = (os.getenv(env_name) or "").strip()
        if key:
            pairs.append((key, role))
    return pairs


def resolve_role(x_api_key: str | None) -> Role | None:
    if not x_api_key:
        return None
    for key, role in _key_roles():
        if secrets.compare_digest(x_api_key, key):
            return role
    return None


def _ops_key_configured() -> bool:
    return bool((os.getenv("API_OPS_KEY") or "").strip())


def _attach(request: Request, *, role: Role, actor: str) -> Role:
    request.state.api_role = role
    request.state.api_actor = actor
    return role


def require_api_key(
    request: Request,
    x_api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> Role:
    """Aceita Bearer (sessão) ou X-API-Key (máquina)."""
    settings = get_settings()

    token = (bearer.credentials if bearer else None) or ""
    if token and is_session_token(token):
        sess = parse_session(token)
        if not sess:
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        role = str(sess["role"])
        if role not in BUSINESS_ROLES:
            raise HTTPException(status_code=401, detail="Sessão com role inválido")
        return _attach(request, role=role, actor=str(sess["username"]))  # type: ignore[arg-type]

    if not settings.api_key_required:
        return _attach(request, role="admin", actor="dev-open")

    pairs = _key_roles()
    if not pairs:
        raise HTTPException(status_code=503, detail="API key não configurada no servidor")

    role = resolve_role(x_api_key)
    if role is None:
        raise HTTPException(status_code=401, detail="API key inválida ou em falta")

    return _attach(request, role=role, actor="api-key")


def require_admin(role: Role = Depends(require_api_key)) -> Role:
    """Staff do backoffice (não ops quando API_OPS_KEY está definida)."""
    if _ops_key_configured() and role == "ops":
        raise HTTPException(
            status_code=403,
            detail="Chave/role ops não acede ao catálogo — use login admin ou API_SECRET_KEY.",
        )
    return role


def require_ops(role: Role = Depends(require_api_key)) -> Role:
    if _ops_key_configured() and role != "ops":
        raise HTTPException(status_code=403, detail="Operação exige role/chave ops.")
    if role not in ("ops", "admin"):
        raise HTTPException(status_code=403, detail="Operação exige role ops ou admin.")
    return role


def require_mensagens(role: Role = Depends(require_api_key)) -> Role:
    assert_dedicated_access("contact_messages", role)
    return role


def require_pedidos(role: Role = Depends(require_api_key)) -> Role:
    assert_dedicated_access("pedidos_orcamento", role)
    return role


def require_catalog_role(role: Role = Depends(require_api_key)) -> Role:
    assert_dedicated_access("catalog", role)
    return role


def role_can_use_dedicated(role: str, resource: str) -> bool:
    if role == "admin":
        return True
    if resource in ("contact_messages", "contacto") and role == "mensagens":
        return True
    if resource in ("pedidos_orcamento", "encomendas_internas", "orcamentos", "encomendas") and role == "pedidos":
        return True
    if resource in ("categories", "catalog", "modelos", "produtos") and role == "catalog":
        return True
    return False


def role_can_access_table(role: str, table: str) -> bool:
    from models.catalog_registry import all_colors_tables, all_model_tables, all_product_tables

    if table in CRUD_INFRA_BLOCKED:
        return False
    if role == "ops":
        return False
    if role == "admin":
        return True
    if table in SENSITIVE_BUSINESS_TABLES:
        return role_can_use_dedicated(role, table)
    if role == "catalog":
        return (
            table in ("categories", "modelos", "produtos")
            or table.startswith("modelos_")
            or table.startswith("produtos_")
            or table in all_model_tables()
            or table in all_product_tables()
            or table in all_colors_tables()
        )
    if role == "pedidos":
        return table in ("pedidos_orcamento", "encomendas_internas")
    if role == "mensagens":
        return table == "contact_messages"
    return False


def assert_table_action(table: str, action: Action, role: Role) -> None:
    if table in CRUD_INFRA_BLOCKED:
        raise HTTPException(
            status_code=403,
            detail="Tabela infra/audit fora do CRUD genérico.",
        )
    if role == "ops":
        raise HTTPException(status_code=403, detail="Role ops sem acesso a CRUD.")
    if not role_can_access_table(role, table):
        raise HTTPException(status_code=403, detail=f"Role '{role}' sem acesso a '{table}'.")
    if action == "hard_delete":
        if table in SENSITIVE_BUSINESS_TABLES:
            raise HTTPException(status_code=403, detail="Hard delete bloqueado em tabelas sensíveis.")
        if role == "admin":
            return
        if role == "catalog" and role_can_access_table(role, table):
            return
        raise HTTPException(status_code=403, detail="Hard delete só para admin ou catálogo.")


def assert_dedicated_access(resource: str, role: Role) -> None:
    if not role_can_use_dedicated(role, resource):
        raise HTTPException(status_code=403, detail=f"Role '{role}' sem acesso a '{resource}'.")


def filter_sidebar_for_role(sidebar: dict, role: str) -> dict:
    if role == "admin":
        return sidebar
    if role == "ops":
        return {}
    out = {}
    for key, cfg in sidebar.items():
        if role_can_access_table(role, key) or role_can_use_dedicated(role, key):
            out[key] = cfg
    return out
