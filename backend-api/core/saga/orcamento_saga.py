"""Saga: pedido de orçamento (BD → email → outbox se falhar)."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from core.cqrs.queries.catalog import resolve_line_display
from core.database import get_db
from core.notify import contact_notify_email
from core.outbox import enqueue_event
from core.resilience import log_dlq_event
from core.saga.logging import saga_log_async
from models.schemas import MIN_ORCAMENTO_TEXTO, PedidoOrcamentoLinha
from utils.email_sender import send_email_async

logger = logging.getLogger("diomika-saga")


@dataclass
class OrcamentoSagaResult:
    pedido_id: str
    saga_id: str
    email_sent: bool
    status: str


def _build_email_body(body: dict[str, Any], pedido_id: str, linhas: list[PedidoOrcamentoLinha]) -> tuple[str, str]:
    lines_text = []
    for linha in linhas:
        info = resolve_line_display(linha.ean, linha.numero_cor, getattr(linha, "altura", None))
        alt_txt = f" | Altura {info.get('altura')}" if info.get("altura") else ""
        lines_text.append(
            f"- {info['modelo']} {info['dimensoes']} | Cor {linha.numero_cor} ({info['cor_nome']}) | "
            f"EAN {linha.ean}{alt_txt} | Qtd {linha.quantidade}"
        )
    email_body = (
        f"Novo pedido de orcamento (#{str(pedido_id)[:8]})\n\n"
        f"Cliente: {body['nome']}\nEmail: {body['email']}\n"
        f"Contacto: {body.get('contacto') or '-'}\n\n"
        f"Linhas:\n" + "\n".join(lines_text) + f"\n\n{MIN_ORCAMENTO_TEXTO}\n"
    )
    if body.get("observacoes"):
        email_body += f"\nObservacoes:\n{body['observacoes']}\n"
    subject = f"[Diomika] Pedido de orcamento — {body['nome']}"
    return subject, email_body


async def run_orcamento_submission_saga(
    body: dict[str, Any],
    linhas: list[PedidoOrcamentoLinha],
) -> OrcamentoSagaResult:
    saga_id = str(uuid4())
    db = get_db()

    linhas_json = [l.model_dump() for l in linhas]
    record = {
        "nome": body["nome"].strip(),
        "email": str(body["email"]),
        "contacto": body.get("contacto"),
        "empresa": body.get("empresa"),
        "observacoes": body.get("observacoes"),
        "linhas": linhas_json,
        "lida": False,
        "visibilidade": True,
        "status": "Nova",
    }

    await saga_log_async(saga_id, "orcamento_submission", "persist_pedido", "running", {"email": body["email"]})

    try:
        res = await asyncio.to_thread(lambda: db.table("pedidos_orcamento").insert(record).execute())
        pedido = res.data[0]
        pedido_id = str(pedido["id"])
    except Exception as exc:
        await saga_log_async(saga_id, "orcamento_submission", "persist_pedido", "failed", {"error": str(exc)})
        log_dlq_event("ORCAMENTO_SAGA_DB", saga_id, exc)
        raise

    await saga_log_async(saga_id, "orcamento_submission", "persist_pedido", "completed", {"pedido_id": pedido_id})

    notify = contact_notify_email()
    if not notify:
        await saga_log_async(saga_id, "orcamento_submission", "send_notification", "skipped", {"reason": "no notify email"})
        await saga_log_async(saga_id, "orcamento_submission", "complete", "completed", {"pedido_id": pedido_id})
        return OrcamentoSagaResult(pedido_id=pedido_id, saga_id=saga_id, email_sent=False, status="Nova")

    subject, email_body = _build_email_body(body, pedido_id, linhas)

    await saga_log_async(saga_id, "orcamento_submission", "send_notification", "running", {"pedido_id": pedido_id})

    email_sent = await send_email_async(to_email=notify, subject=subject, body=email_body)

    if email_sent:
        await saga_log_async(saga_id, "orcamento_submission", "send_notification", "completed", {"pedido_id": pedido_id})
        await saga_log_async(saga_id, "orcamento_submission", "complete", "completed", {"pedido_id": pedido_id})
        return OrcamentoSagaResult(pedido_id=pedido_id, saga_id=saga_id, email_sent=True, status="Nova")

    await asyncio.to_thread(lambda: db.table("pedidos_orcamento").update({"status": "Email pendente"}).eq("id", pedido_id).execute())
    await asyncio.to_thread(
        enqueue_event,
        "orcamento_notification",
        {
            "pedido_id": pedido_id,
            "notify_to": notify,
            "subject": subject,
            "body": email_body,
        },
    )
    await saga_log_async(saga_id, "orcamento_submission", "send_notification", "compensated", {"outbox": True, "pedido_id": pedido_id})
    await saga_log_async(saga_id, "orcamento_submission", "complete", "completed", {"pedido_id": pedido_id, "email_pending": True})
    return OrcamentoSagaResult(pedido_id=pedido_id, saga_id=saga_id, email_sent=False, status="Email pendente")
