"""Pedidos de orcamento do site (carrinho) — saga + idempotência."""
from __future__ import annotations

import io
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field, field_validator

from core.audit import audit_request
from core.auth import require_pedidos
from core.local_only import admin_must_be_local
from core.order_enrich import enrich_order_lines
from core.database import get_db
from core.text_safe import normalize_text
from core.idempotency import (
    IdempotencyUnavailable,
    abort_idempotent_request,
    begin_idempotent_request,
    complete_idempotent_request,
    get_cached_response,
)
from core.rate_limit import MAX_PUBLIC_BODY_LINES, MAX_LINE_QUANTITY, get_client_ip, rate_limit
from core.saga.orcamento_saga import run_orcamento_submission_saga
from core.validators.order_lines import validate_order_lines
from models.schemas import PedidoOrcamentoLinha
from utils.pdf_encomenda import build_pedido_pdf

logger = logging.getLogger("diomika-api")

router = APIRouter(prefix="/orcamentos", tags=["Orcamentos"])
supabase = get_db()

IDEMPOTENCY_OP = "SUBMIT_ORCAMENTO"


class OrcamentoRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    contacto: str | None = Field(None, max_length=30)
    empresa: str | None = Field(None, max_length=200)
    observacoes: str | None = Field(None, max_length=5000)
    linhas: list[PedidoOrcamentoLinha] = Field(..., min_length=1, max_length=MAX_PUBLIC_BODY_LINES)
    website: str | None = None
    cf_turnstile_response: str | None = None

    @field_validator("nome", "contacto", "empresa", "observacoes", mode="before")
    @classmethod
    def _nfc(cls, v: object) -> object:
        if isinstance(v, str):
            return normalize_text(v)
        return v


def _success_payload(pedido_id: str, status: str = "Nova") -> dict:
    return {
        "status": "success",
        "message": "Pedido de orcamento enviado. Entraremos em contacto em breve.",
        "id": pedido_id,
        "pedido_status": status,
    }


@router.post("")
async def submit_orcamento(
    body: OrcamentoRequest,
    request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    from core.feature_flags import flag

    if not flag("ORCAMENTO_FORM", True):
        raise HTTPException(status_code=503, detail="Formulário temporariamente indisponível.")
    rate_limit(request, "orcamento_form", max_calls=5, window_seconds=60)

    if body.website:
        raise HTTPException(status_code=400, detail="Pedido invalido")

    key = (idempotency_key or "").strip()
    from core.config import get_settings

    if get_settings().is_production and not key:
        raise HTTPException(status_code=400, detail="Idempotency-Key obrigatória.")
    if key and len(key) > 128:
        raise HTTPException(status_code=400, detail="Idempotency-Key inválida")

    from utils.turnstile import verify_turnstile_async

    try:
        await verify_turnstile_async(body.cf_turnstile_response, get_client_ip(request))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
            raise HTTPException(
                status_code=409,
                detail="Pedido identico em processamento. Aguarde e tente novamente.",
            )

    try:
        validate_order_lines(body.linhas)
        for linha in body.linhas:
            if linha.quantidade > MAX_LINE_QUANTITY:
                raise HTTPException(
                    status_code=400,
                    detail=f"Quantidade máxima por linha: {MAX_LINE_QUANTITY}.",
                )
    except HTTPException:
        if key:
            abort_idempotent_request(key, IDEMPOTENCY_OP)
        raise

    try:
        result = await run_orcamento_submission_saga(
            body.model_dump(exclude={"website", "cf_turnstile_response"}),
            body.linhas,
        )
        payload = _success_payload(result.pedido_id, result.status)
        if key:
            complete_idempotent_request(key, IDEMPOTENCY_OP, payload)
        return payload
    except HTTPException:
        if key:
            abort_idempotent_request(key, IDEMPOTENCY_OP)
        raise
    except Exception as exc:
        if key:
            abort_idempotent_request(key, IDEMPOTENCY_OP)
        logger.error("Erro saga orcamento: %s", exc)
        raise HTTPException(status_code=500, detail="Nao foi possivel registar o pedido.") from exc


@router.get(
    "/{pedido_id}/pdf",
    dependencies=[Depends(admin_must_be_local), Depends(require_pedidos)],
)
def download_orcamento_pdf(request: Request, pedido_id: str):
    try:
        res = supabase.table("pedidos_orcamento").select("*").eq("id", pedido_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    if not res.data:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")

    row = res.data
    linhas = enrich_order_lines(row.get("linhas") or [])
    extra = [f"Email: {row.get('email', '')}"]
    if row.get("contacto"):
        extra.append(f"Contacto: {row['contacto']}")
    if row.get("empresa"):
        extra.append(f"Empresa: {row['empresa']}")
    pdf_bytes = build_pedido_pdf("Diomika — Pedido de orcamento", row.get("nome", ""), linhas, extra)
    audit_request(request, action="export_pdf", resource="pedidos_orcamento", resource_id=pedido_id)

    filename = f"orcamento_{str(pedido_id)[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
