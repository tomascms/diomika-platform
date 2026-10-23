#!/usr/bin/env python3
"""Apaga/anonimiza PII por email — direito ao apagamento (RGPD)."""
from __future__ import annotations

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
            res = db.table(table).delete().eq(col, email).execute()
            counts[table] = len(res.data or [])
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
        detail={"email": email, "counts": counts},
    )
    return {"ok": True, "email": email, "deleted": counts}
