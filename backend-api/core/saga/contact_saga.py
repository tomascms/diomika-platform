"""Saga: submissão de contacto (DB → email → outbox se falhar)."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from core.database import get_db
from core.notify import contact_notify_email
from core.outbox import enqueue_event
from core.resilience import log_dlq_event
from core.saga.logging import saga_log_async
from utils.email_sender import send_email_async

logger = logging.getLogger("diomika-saga")


@dataclass
class ContactSagaResult:
    message_id: str
    saga_id: str
    email_sent: bool
    status: str


async def run_contact_submission_saga(msg_data: dict[str, Any]) -> ContactSagaResult:
    saga_id = str(uuid4())
    message_id = str(uuid4())
    db = get_db()

    await saga_log_async(saga_id, "contact_submission", "persist_message", "running", {"message_id": message_id})

    payload = dict(msg_data)
    payload["id"] = message_id
    payload["status"] = "Nova"
    payload["lida"] = False
    payload["last_sender"] = "client"

    try:
        await asyncio.to_thread(lambda: db.table("contact_messages").insert(payload).execute())
    except Exception as exc:
        await saga_log_async(saga_id, "contact_submission", "persist_message", "failed", {"error": str(exc)})
        log_dlq_event("CONTACT_SAGA_DB", message_id, exc)
        raise

    await saga_log_async(saga_id, "contact_submission", "persist_message", "completed", {"message_id": message_id})

    notify_to = contact_notify_email()
    if not notify_to:
        await saga_log_async(saga_id, "contact_submission", "send_notification", "skipped", {"reason": "no notify email"})
        return ContactSagaResult(message_id=message_id, saga_id=saga_id, email_sent=False, status="Nova")

    ref_id = f"[Ref: #{message_id[:8]}]"
    subject = f"[Diomika] Contacto — {msg_data.get('assunto', 'Sem assunto')} {ref_id}"
    email_body = (
        f"Nova mensagem de contacto\n\n"
        f"De: {msg_data.get('nome')} ({msg_data.get('email')})\n"
        f"Contacto: {msg_data.get('contacto')}\n\n"
        f"Assunto: {msg_data.get('assunto')}\n\n"
        f"Mensagem:\n{msg_data.get('mensagem')}\n"
    )

    await saga_log_async(saga_id, "contact_submission", "send_notification", "running", {"message_id": message_id})
    email_sent = await send_email_async(to_email=notify_to, subject=subject, body=email_body)

    if email_sent:
        await saga_log_async(saga_id, "contact_submission", "send_notification", "completed", {"message_id": message_id})
        await saga_log_async(saga_id, "contact_submission", "complete", "completed", {"message_id": message_id})
        return ContactSagaResult(message_id=message_id, saga_id=saga_id, email_sent=True, status="Nova")

    await asyncio.to_thread(lambda: db.table("contact_messages").update({"status": "Email pendente"}).eq("id", message_id).execute())
    await asyncio.to_thread(
        enqueue_event,
        "contact_notification",
        {"message_id": message_id, "notify_to": notify_to, "subject": subject, "body": email_body},
    )
    await saga_log_async(saga_id, "contact_submission", "send_notification", "compensated", {"outbox": True})
    await saga_log_async(saga_id, "contact_submission", "complete", "completed", {"message_id": message_id, "email_pending": True})
    return ContactSagaResult(message_id=message_id, saga_id=saga_id, email_sent=False, status="Email pendente")
