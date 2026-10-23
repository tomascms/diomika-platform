"""Workers em background dentro da API — 1 processo (VM / Docker)."""
from __future__ import annotations

import asyncio
import logging
import os
import threading
import time

logger = logging.getLogger("background-workers")

_stop = threading.Event()
_threads: list[threading.Thread] = []
_lock_handle = None


def _acquire_single_runner_lock() -> bool:
    """Com vários processos uvicorn (UVICORN_WORKERS=2), só um corre os workers.

    Antes, cada processo lia a mesma caixa IMAP e a mesma fila outbox no mesmo
    segundo — duas cópias a competir (respostas de clientes podiam entrar em
    duplicado na conversa). O lock do SO é libertado se o processo morrer; o
    processo que o uvicorn arranca a seguir fica com ele.
    """
    global _lock_handle
    try:
        import fcntl
    except ImportError:  # Windows (dev): um só processo
        return True
    path = os.getenv("WORKER_LOCK_FILE", "/tmp/diomika-embedded-workers.lock")
    handle = open(path, "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return False
    _lock_handle = handle
    return True


def should_run_embedded() -> bool:
    explicit = (os.getenv("RUN_EMBEDDED_WORKERS") or "").strip().lower()
    if explicit in ("0", "false", "no"):
        return False
    if explicit in ("1", "true", "yes"):
        return True
    from core.config import get_settings

    return get_settings().is_production


def _email_loop() -> None:
    from workers.email_worker import process_inbox

    poll = int(os.getenv("EMAIL_POLL_SECONDS", "30"))
    logger.info("Email worker embutido (poll=%ss)", poll)
    while not _stop.is_set():
        try:
            process_inbox()
        except Exception as exc:
            logger.error("Email worker: %s", exc)
        _stop.wait(poll)


def _outbox_loop() -> None:
    from workers.outbox_worker import run_once

    poll = int(os.getenv("OUTBOX_POLL_SECONDS", "30"))
    logger.info("Outbox worker embutido (poll=%ss)", poll)
    while not _stop.is_set():
        try:
            n = asyncio.run(run_once())
            if n:
                logger.info("Outbox: %s evento(s) processado(s)", n)
        except Exception as exc:
            logger.error("Outbox worker: %s", exc)
        _stop.wait(poll)


def _maintenance_loop() -> None:
    from core.idempotency_maintenance import purge_expired_idempotency_keys
    from core.retention import purge_expired_pii
    from core.saga.maintenance import sweep_zombie_sagas

    poll = int(os.getenv("SAGA_SWEEP_SECONDS", "300"))
    retention_every = max(1, int(os.getenv("RETENTION_SWEEP_CYCLES", "12")))  # ~1h se poll=300
    cycle = 0
    logger.info("Manutenção embutida (sagas + idempotency + retention, poll=%ss)", poll)
    while not _stop.is_set():
        try:
            n = sweep_zombie_sagas()
            if n:
                logger.warning("Sagas zombie corrigidas: %s", n)
        except Exception as exc:
            logger.error("Saga maintenance: %s", exc)
        try:
            purged = purge_expired_idempotency_keys()
            if purged:
                logger.info("Idempotency expiradas removidas: %s", purged)
        except Exception as exc:
            logger.error("Idempotency maintenance: %s", exc)
        cycle += 1
        if cycle >= retention_every:
            cycle = 0
            try:
                purge_expired_pii()
            except Exception as exc:
                logger.error("Retention: %s", exc)
        _stop.wait(poll)


def start_background_workers() -> None:
    if not should_run_embedded():
        logger.info("Workers embutidos desactivados (RUN_EMBEDDED_WORKERS)")
        return
    if _threads:
        return
    if not _acquire_single_runner_lock():
        logger.info("Workers embutidos já a correr noutro processo da API — este só serve pedidos")
        return

    for target, name in (
        (_email_loop, "email"),
        (_outbox_loop, "outbox"),
        (_maintenance_loop, "saga-maint"),
    ):
        t = threading.Thread(target=target, name=f"diomika-{name}", daemon=True)
        t.start()
        _threads.append(t)
    logger.info("Workers embutidos iniciados (API + email + outbox + manutenção num processo)")


def stop_background_workers() -> None:
    _stop.set()
    for t in _threads:
        t.join(timeout=5)
    _threads.clear()
