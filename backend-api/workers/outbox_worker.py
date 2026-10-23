"""Worker que processa eventos pendentes na outbox."""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))

from core.env_loader import load_project_env

load_project_env()

from core.outbox import claim_pending, mark_done, mark_failed
from utils.email_sender import send_email_async

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("outbox-worker")

POLL_SECONDS = int(os.getenv("OUTBOX_POLL_SECONDS", "30"))


async def process_event(event: dict) -> None:
    event_id = event["id"]
    event_type = event["event_type"]
    payload = event.get("payload") or {}
    attempts = int(event.get("attempts") or 0) + 1
    max_attempts = int(event.get("max_attempts") or 5)

    try:
        if event_type == "contact_notification":
            ok = await send_email_async(
                to_email=payload["notify_to"],
                subject=payload["subject"],
                body=payload["body"],
                reply_to=payload.get("reply_to"),
            )
            if not ok:
                raise RuntimeError("SMTP falhou")
            mark_done(event_id)
            logger.info("Outbox %s processado", event_id[:8])
        elif event_type == "orcamento_notification":
            ok = await send_email_async(
                to_email=payload["notify_to"],
                subject=payload["subject"],
                body=payload["body"],
            )
            if not ok:
                raise RuntimeError("SMTP falhou")
            pedido_id = payload.get("pedido_id")
            if pedido_id:
                from core.database import get_db

                get_db().table("pedidos_orcamento").update({"status": "Nova"}).eq("id", pedido_id).execute()
            mark_done(event_id)
            logger.info("Outbox orcamento %s processado", event_id[:8])
        else:
            mark_failed(event_id, f"Tipo desconhecido: {event_type}", attempts, max_attempts)
    except Exception as exc:
        mark_failed(event_id, str(exc), attempts, max_attempts)
        logger.error("Outbox %s falhou: %s", event_id[:8], exc)


async def run_once() -> int:
    events = claim_pending()
    for event in events:
        await process_event(event)
    return len(events)


def main() -> None:
    logger.info("Outbox worker iniciado (poll=%ss)", POLL_SECONDS)
    while True:
        try:
            n = asyncio.run(run_once())
            if n:
                logger.info("Processados %s eventos", n)
        except Exception as exc:
            logger.error("Erro no outbox worker: %s", exc)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
