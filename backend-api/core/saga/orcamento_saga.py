"""Saga: pedido de orçamento (BD → email → outbox se falhar)."""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from core import company
from core.catalog_storefront import resolve_product_lines_batch
from core.database import get_db
from core.notify import contact_notify_email
from core.origem import clean_origem
from core.outbox import enqueue_event
from core.resilience import log_dlq_event
from core.saga.logging import saga_log_async
from models.schemas import MIN_ORCAMENTO_TEXTO, PedidoOrcamentoLinha
from utils.email_sender import send_email_async

logger = logging.getLogger("diomika-saga")

# Colunas acrescentadas por db/migrations/2026-10-28_pedidos_orcamento_b2b.sql: só seguem para a BD com valor,
# por isso um pedido sem elas grava-se mesmo antes de a migração estar aplicada.
_B2B_COLUMNS = ("nif", "localidade", "tipo_cliente")  # + `origem` (2026-11-02_new_columns.sql), tratada à parte


@dataclass
class OrcamentoSagaResult:
    pedido_id: str
    saga_id: str
    email_sent: bool
    status: str


def _receipt_enabled() -> bool:
    """Recibo ao comprador: desligado por omissão (QUOTE_RECEIPT_EMAIL=1 liga).

    O remetente é MAIL_FROM, que o comprador vê: hoje é a caixa pessoal do prestador, por isso só se liga
    quando o remetente for uma caixa da empresa.
    """
    return (os.getenv("QUOTE_RECEIPT_EMAIL") or "").strip().lower() in ("1", "true", "yes", "on")


def _line_texts(linhas: list[PedidoOrcamentoLinha]) -> list[str]:
    # Uma só consulta para todas as linhas (eram 2 por linha, dentro do event loop: API-03).
    resolved = resolve_product_lines_batch(
        [{"ean": l.ean, "numero_cor": l.numero_cor, "altura": getattr(l, "altura", None) or ""} for l in linhas]
    )
    lines_text = []
    for linha, info in zip(linhas, resolved):
        alt_txt = f" | Altura {info.get('altura')}" if info.get("altura") else ""
        lines_text.append(
            f"- {info['modelo']} {info['dimensoes']} | Cor {linha.numero_cor} ({info['cor_nome']}) | "
            f"EAN {linha.ean}{alt_txt} | Qtd {linha.quantidade}"
        )
    return lines_text


def _build_email_body(body: dict[str, Any], pedido_id: str, lines_text: list[str]) -> tuple[str, str]:
    email_body = (
        f"Novo pedido de orcamento (#{str(pedido_id)[:8]})\n\n"
        f"Cliente: {body['nome']}\nEmail: {body['email']}\n"
        f"Contacto: {body.get('contacto') or '-'}\n"
        f"Empresa: {body.get('empresa') or '-'}\n"
        f"NIF: {body.get('nif') or '-'}\n"
        f"Localidade: {body.get('localidade') or '-'}\n"
        f"Compra como: {body.get('tipo_cliente') or '-'}\n\n"
        f"Linhas:\n" + "\n".join(lines_text) + f"\n\n{MIN_ORCAMENTO_TEXTO}\n"
    )
    if body.get("observacoes"):
        email_body += f"\nObservacoes:\n{body['observacoes']}\n"
    subject = f"[Diomika] Pedido de orcamento — {body['nome']}"
    return subject, email_body


def _build_receipt(body: dict[str, Any], pedido_id: str, lines_text: list[str]) -> tuple[str, str]:
    """Recibo para o comprador (RP-05): a referência, o resumo e o que se segue, com a assinatura legal.

    Só leva dados do sistema (a referência e as linhas resolvidas no catálogo): o texto escrito no formulário
    (nome, empresa, observações) não se repete, senão o recibo serviria para mandar texto de um estranho, com a
    nossa assinatura, a qualquer endereço.
    """
    ref = str(pedido_id)[:8]
    receipt_body = (
        "Olá,\n\n"
        f"Recebemos o seu pedido de orçamento n.º {ref}. Indique este número se nos contactar por WhatsApp ou telefone.\n\n"
        f"O que pediu:\n" + "\n".join(lines_text) + "\n\n"
        "O pedido não é vinculativo: a venda só se conclui quando aceitar a nossa proposta. "
        "Respondemos no prazo de 1 dia útil.\n\n"
        "Usamos os dados que nos indicou para lhe responder. "
        f"Política de Privacidade: {company.SITE}/privacidade\n"
        f"Condições gerais de venda: {company.SITE}/condicoes-de-venda\n\n"
        f"{company.legal_signature()}\n"
    )
    return f"Recebemos o seu pedido de orçamento n.º {ref}", receipt_body


async def _send_receipt(saga_id: str, body: dict[str, Any], pedido_id: str, lines_text: list[str]) -> None:
    """Melhor esforço: o comprador já vê a referência no ecrã, por isso uma falha aqui só fica no registo."""
    await saga_log_async(saga_id, "orcamento_submission", "send_receipt", "running", {"pedido_id": pedido_id})
    subject, receipt_body = _build_receipt(body, pedido_id, lines_text)
    sent = await send_email_async(to_email=str(body["email"]), subject=subject, body=receipt_body)
    await saga_log_async(
        saga_id, "orcamento_submission", "send_receipt", "completed" if sent else "failed", {"pedido_id": pedido_id}
    )


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
    record.update({column: body[column] for column in _B2B_COLUMNS if body.get(column)})
    if origem := clean_origem(body.get("origem")):
        record["origem"] = origem

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
    receipt = _receipt_enabled()
    # Uma só ronda de consultas ao catálogo para os dois emails (e nenhuma se não houver nenhum a enviar).
    lines_text = await asyncio.to_thread(_line_texts, linhas) if notify or receipt else []

    if not notify:
        await saga_log_async(saga_id, "orcamento_submission", "send_notification", "skipped", {"reason": "no notify email"})
        await saga_log_async(saga_id, "orcamento_submission", "complete", "completed", {"pedido_id": pedido_id})
        result = OrcamentoSagaResult(pedido_id=pedido_id, saga_id=saga_id, email_sent=False, status="Nova")
    else:
        subject, email_body = _build_email_body(body, pedido_id, lines_text)

        await saga_log_async(saga_id, "orcamento_submission", "send_notification", "running", {"pedido_id": pedido_id})

        email_sent = await send_email_async(to_email=notify, subject=subject, body=email_body)

        if email_sent:
            await saga_log_async(saga_id, "orcamento_submission", "send_notification", "completed", {"pedido_id": pedido_id})
            await saga_log_async(saga_id, "orcamento_submission", "complete", "completed", {"pedido_id": pedido_id})
            result = OrcamentoSagaResult(pedido_id=pedido_id, saga_id=saga_id, email_sent=True, status="Nova")
        else:
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
            result = OrcamentoSagaResult(pedido_id=pedido_id, saga_id=saga_id, email_sent=False, status="Email pendente")

    if receipt:
        await _send_receipt(saga_id, body, pedido_id, lines_text)
    return result
