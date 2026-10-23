from __future__ import annotations

import asyncio

import logging
import os
import re
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field, field_validator

from core.audit import audit_request
from core.auth import require_mensagens
from core.config import get_settings
from core.local_only import admin_must_be_local
from core.database import get_db
from core.text_safe import normalize_text
from core.idempotency import (
    IdempotencyUnavailable,
    abort_idempotent_request,
    begin_idempotent_request,
    complete_idempotent_request,
    get_cached_response,
)
from core.rate_limit import get_client_ip, rate_limit
from core.saga.contact_saga import run_contact_submission_saga
from utils.email_body import strip_email_quotes
from utils.email_sender import send_email_async
from utils.turnstile import verify_turnstile_async

IDEMPOTENCY_OP = "SUBMIT_CONTACT"

logger = logging.getLogger("diomika-api")
router = APIRouter(prefix="/contacto", tags=["Contacto"])
supabase = get_db()


class ContactRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    contacto: str = Field(..., min_length=6, max_length=20)
    assunto: str = Field(..., min_length=3, max_length=200)
    mensagem: str = Field(..., min_length=10, max_length=5000)
    website: str | None = None  # honeypot — deve ficar vazio
    cf_turnstile_response: str | None = None

    @field_validator("nome", "contacto", "assunto", "mensagem", mode="before")
    @classmethod
    def _nfc(cls, v: object) -> object:
        if isinstance(v, str):
            return normalize_text(v)
        return v


class ReplyRequest(BaseModel):
    corpo_resposta: str = Field(..., min_length=1, max_length=10000)

    @field_validator("corpo_resposta", mode="before")
    @classmethod
    def _nfc(cls, v: object) -> object:
        if isinstance(v, str):
            return normalize_text(v)
        return v


@router.post("")
async def send_message(
    msg: ContactRequest,
    request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """Formulario publico — saga DB + email + outbox."""
    from core.feature_flags import flag

    if not flag("CONTACT_FORM", True):
        raise HTTPException(status_code=503, detail="Formulário temporariamente indisponível.")
    rate_limit(request, "contact_form", max_calls=5, window_seconds=60)

    key = (idempotency_key or "").strip()
    if get_settings().is_production and not key:
        raise HTTPException(status_code=400, detail="Idempotency-Key obrigatória.")
    if key and len(key) > 128:
        raise HTTPException(status_code=400, detail="Idempotency-Key inválida")

    if key:
        try:
            cached = get_cached_response(key, IDEMPOTENCY_OP)
        except IdempotencyUnavailable:
            raise HTTPException(status_code=503, detail="Serviço temporariamente indisponível.") from None
        if cached:
            return cached
        state = begin_idempotent_request(key, IDEMPOTENCY_OP)
        if state == "unavailable":
            raise HTTPException(status_code=503, detail="Serviço temporariamente indisponível.")
        if state == "cached":
            cached = get_cached_response(key, IDEMPOTENCY_OP)
            if cached:
                return cached
        if state == "in_progress":
            raise HTTPException(status_code=409, detail="Pedido em processamento. Aguarde.")

    if msg.website:
        logger.warning("Honeypot activado de %s", request.client.host if request.client else "?")
        raise HTTPException(status_code=400, detail="Pedido inválido")

    try:
        await verify_turnstile_async(msg.cf_turnstile_response, get_client_ip(request))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = await run_contact_submission_saga(
            msg.model_dump(exclude={"website", "cf_turnstile_response"})
        )
    except Exception as e:
        logger.error("Erro na saga de contacto: %s", e)
        if key:
            abort_idempotent_request(key, IDEMPOTENCY_OP)
        raise HTTPException(status_code=400, detail="Não foi possível enviar a mensagem. Tente mais tarde.") from e

    payload = {
        "status": "success",
        "message": "Mensagem enviada com sucesso",
        "email_notified": result.email_sent,
        "message_status": result.status,
    }
    if key:
        complete_idempotent_request(key, IDEMPOTENCY_OP, payload)
    return payload


@router.get("", dependencies=[Depends(admin_must_be_local), Depends(require_mensagens)])
def get_messages(limit: int = 100, offset: int = 0):
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    try:
        res = (
            supabase.table("contact_messages")
            .select("*")
            .order("lida")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        rows = res.data or []
        return {"items": rows, "limit": limit, "offset": offset, "count": len(rows)}
    except Exception as e:
        logger.error("Erro ao listar mensagens: %s", e)
        raise HTTPException(status_code=500, detail="Erro ao carregar mensagens") from e


@router.get(
    "/{message_id}",
    dependencies=[Depends(admin_must_be_local), Depends(require_mensagens)],
)
def get_message(message_id: str):
    try:
        res = supabase.table("contact_messages").select("*").eq("id", message_id).single().execute()
    except Exception as e:
        logger.error("Erro ao buscar mensagem %s: %s", message_id, e)
        raise HTTPException(status_code=404, detail="Mensagem não encontrada.") from e

    if not res.data:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada.")

    history_res = (
        supabase.table("message_history")
        .select("*")
        .eq("message_id", message_id)
        .order("created_at")
        .execute()
    )
    mail_from = (os.getenv("MAIL_FROM") or os.getenv("MAIL_USERNAME") or "").lower()
    history = []
    for row in history_res.data or []:
        sender = (row.get("sender_email") or "").lower()
        history.append(
            {
                **row,
                "body": strip_email_quotes(row.get("body") or ""),
                "role": "vendor" if mail_from and mail_from in sender else "client",
            }
        )
    return {"message": res.data, "history": history}


@router.patch(
    "/{message_id}/lida",
    dependencies=[Depends(admin_must_be_local), Depends(require_mensagens)],
)
def mark_read(request: Request, message_id: UUID, lida: bool = True):
    res = supabase.table("contact_messages").update({"lida": lida}).eq("id", str(message_id)).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada")
    audit_request(
        request,
        action="mark_read",
        resource="contact_messages",
        resource_id=str(message_id),
        detail={"lida": lida},
    )
    return {"status": "ok", "lida": lida}


@router.post(
    "/responder/{message_id}",
    dependencies=[Depends(admin_must_be_local), Depends(require_mensagens)],
)
async def reply_to_message(request: Request, message_id: str, reply: ReplyRequest):
    try:
        res = await asyncio.to_thread(
            lambda: supabase.table("contact_messages").select("*").eq("id", message_id).single().execute()
        )
    except Exception as e:
        logger.error("Erro ao buscar mensagem %s: %s", message_id, e)
        raise HTTPException(status_code=404, detail="Mensagem original nao encontrada.") from e

    if not res.data:
        raise HTTPException(status_code=404, detail="Mensagem original nao encontrada.")

    original_msg = res.data
    ref_id = f"[Ref: #{message_id[:8]}]"
    original_subject = original_msg.get("assunto", "")
    clean_subject = re.sub(r"\[Ref: #\w+\]", "", original_subject).strip()
    if not clean_subject.lower().startswith("re:"):
        new_subject = f"Re: {clean_subject} {ref_id}"
    else:
        new_subject = f"{clean_subject} {ref_id}"

    email_sent = await send_email_async(
        to_email=original_msg["email"],
        subject=new_subject,
        body=reply.corpo_resposta,
        thread_id=message_id,
    )
    if not email_sent:
        raise HTTPException(status_code=500, detail="Falha no servico de envio de email.")

    mail_from = os.getenv("MAIL_FROM") or os.getenv("MAIL_USERNAME") or "sistema@diomika"

    def _record_reply() -> None:
        supabase.table("message_history").insert(
            {"message_id": message_id, "sender_email": mail_from, "body": reply.corpo_resposta.strip()}
        ).execute()
        supabase.table("contact_messages").update(
            {"status": "Respondida", "lida": True, "last_sender": "vendor"}
        ).eq("id", message_id).execute()

    try:
        await asyncio.to_thread(_record_reply)
    except Exception:
        # O email já saiu: não devolver 500 (o backoffice reenviaria). Fica no log para corrigir à mão.
        logger.exception("Resposta enviada mas não registada (mensagem %s)", message_id)

    audit_request(request, action="reply", resource="contact_messages", resource_id=message_id)
    return {"status": "success", "message": f"Resposta enviada para {original_msg['email']}"}
