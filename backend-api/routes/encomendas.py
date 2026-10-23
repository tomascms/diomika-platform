"""Encomendas internas (padrao) + PDF."""
from __future__ import annotations

import io
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.audit import audit_request
from core.auth import require_pedidos
from core.local_only import admin_must_be_local
from core.order_enrich import enrich_order_lines
from core.database import get_db
from core.validators.order_lines import validate_order_lines
from models.schemas import EncomendaInternaLinha
from utils.pdf_encomenda import build_pedido_pdf

logger = logging.getLogger("diomika-api")

router = APIRouter(
    prefix="/encomendas-internas",
    tags=["Encomendas internas"],
    dependencies=[Depends(admin_must_be_local), Depends(require_pedidos)],
)
supabase = get_db()


class EncomendaInternaCreate(BaseModel):
    referencia_cliente: str = Field(..., min_length=1, max_length=200)
    linhas: list[EncomendaInternaLinha] = Field(..., min_length=1)


@router.post("")
def create_encomenda(request: Request, body: EncomendaInternaCreate):
    validate_order_lines(body.linhas)
    linhas_json = [l.model_dump() for l in body.linhas]
    record = {
        "referencia_cliente": body.referencia_cliente.strip(),
        "linhas": linhas_json,
        "visibilidade": True,
    }
    try:
        res = supabase.table("encomendas_internas").insert(record).execute()
        row = res.data[0]
    except Exception as e:
        logger.error("Erro encomenda interna: %s", e)
        raise HTTPException(status_code=400, detail="Nao foi possivel criar a encomenda.")

    audit_request(
        request,
        action="create",
        resource="encomendas_internas",
        resource_id=str(row.get("id") or ""),
    )
    return {"status": "success", "data": row}


@router.get("/{encomenda_id}/pdf")
def download_pdf(request: Request, encomenda_id: str):
    try:
        res = supabase.table("encomendas_internas").select("*").eq("id", encomenda_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Encomenda nao encontrada")
    if not res.data:
        raise HTTPException(status_code=404, detail="Encomenda nao encontrada")

    row = res.data
    linhas = enrich_order_lines(row.get("linhas") or [])
    pdf_bytes = build_pedido_pdf("Diomika — Encomenda", row["referencia_cliente"], linhas)
    audit_request(request, action="export_pdf", resource="encomendas_internas", resource_id=encomenda_id)

    filename = f"encomenda_{str(encomenda_id)[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
