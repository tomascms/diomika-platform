#!/usr/bin/env python3
"""Apaga/anonimiza PII por email — direito ao apagamento (RGPD)."""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from core.audit import log_admin_action
from core.auth import Role, require_admin
from core.database import get_db
from core.local_only import admin_must_be_local
from core.rate_limit import get_client_ip

logger = logging.getLogger("diomika-privacy")

router = APIRouter(
    prefix="/admin/privacy",
    tags=["Privacy"],
    dependencies=[Depends(admin_must_be_local), Depends(require_admin)],
)


class EraseBody(BaseModel):
    email: EmailStr
    confirm: str = Field(..., description="Escrever ERASE para confirmar")


def _like_literal(value: str) -> str:
    """Valor sem curingas para o ilike: a barra, o % e o _ ficam escapados."""
    return value.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def _erase_rows(db, table: str, col: str, email: str) -> int:
    """Apaga as linhas cujo `lower(email)` é igual: endereços guardados com maiúsculas também (LEGAL-09).

    O PostgREST não filtra por lower(coluna): o ilike apanha os candidatos e a igualdade exacta decide, para um
    curinga (`*` é um no ilike do PostgREST) nunca apagar dados de outra pessoa.
    """
    rows = db.table(table).select(f"id,{col}").ilike(col, _like_literal(email)).execute().data or []
    ids = [r["id"] for r in rows if str(r.get(col) or "").strip().lower() == email]
    if not ids:
        return 0
    res = db.table(table).delete().in_("id", ids).execute()
    return len(res.data or [])


@router.post("/erase")
def erase_by_email(body: EraseBody, request: Request, role: Role = Depends(require_admin)) -> dict[str, Any]:
    """Apaga mensagens/pedidos associados a um email (só role admin)."""
    if role != "admin":
        raise HTTPException(status_code=403, detail="Só admin pode apagar PII")
    if body.confirm != "ERASE":
        raise HTTPException(status_code=400, detail="confirm deve ser exactamente ERASE")
    email = str(body.email).strip().lower()
    db = get_db()
    counts: dict[str, int] = {}
    for table, col in (
        ("contact_messages", "email"),
        ("pedidos_orcamento", "email"),
    ):
        try:
            counts[table] = _erase_rows(db, table, col, email)
        except Exception as exc:
            logger.warning("erase %s: %s", table, exc)
            counts[table] = -1
    log_admin_action(
        action="privacy_erase",
        resource="privacy",
        role=str(role),
        actor=str(getattr(request.state, "api_actor", "")),
        client_ip=get_client_ip(request),
        request_id=getattr(request.state, "request_id", None),
        # Só o resumo: o email que se pediu para apagar não pode ficar um ano no registo de auditoria (SEG-18).
        detail={"email_sha256": hashlib.sha256(email.encode("utf-8")).hexdigest(), "counts": counts},
    )
    return {"ok": True, "email": email, "deleted": counts}
