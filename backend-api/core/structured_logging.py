"""Logging estruturado (JSON) — activo em produção; Axiom se AXIOM_TOKEN."""
from __future__ import annotations

import atexit
import json
import logging
import os
import queue
import threading
import urllib.request
from datetime import datetime, timezone
from logging.handlers import QueueHandler, QueueListener
from typing import Any


_ENV = os.getenv("DIOMIKA_ENV") or "development"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "diomika-api",
            "env": _ENV,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key in ("request_id", "path", "method", "status", "ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


_axiom_lock = threading.Lock()
_axiom_queue: list[dict[str, Any]] = []


class AxiomHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        token = (os.getenv("AXIOM_TOKEN") or "").strip()
        dataset = (os.getenv("AXIOM_DATASET") or "diomika").strip()
        if not token:
            return
        try:
            body = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
            }
        except Exception:
            return
        with _axiom_lock:
            _axiom_queue.append(body)
            batch = list(_axiom_queue) if len(_axiom_queue) >= 5 else None
            if batch:
                _axiom_queue.clear()
        if not batch:
            return
        try:
            from core.ssrf_guard import assert_safe_outbound_url

            # EU org: edge ingest (https://eu-central-1.aws.edge.axiom.co/v1/ingest/{dataset})
            # US legacy: https://api.axiom.co/v1/datasets/{dataset}/ingest
            base = (os.getenv("AXIOM_API_URL") or "https://api.axiom.co").rstrip("/")
            if "edge.axiom.co" in base:
                url = f"{base}/v1/ingest/{dataset}"
            else:
                url = f"{base}/v1/datasets/{dataset}/ingest"
            assert_safe_outbound_url(url)
            req = urllib.request.Request(
                url,
                data=json.dumps(batch).encode("utf-8"),
                method="POST",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "User-Agent": "DiomikaAxiom/1.0",
                },
            )
            urllib.request.urlopen(req, timeout=5).read()
        except Exception:
            pass


def configure_structured_logging() -> None:
    root = logging.getLogger()
    fmt = (os.getenv("LOG_FORMAT") or "").strip().lower()
    if fmt == "json":
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(logging.INFO)
    else:
        if not root.handlers:
            logging.basicConfig(level=logging.INFO)
    # Bibliotecas HTTP registavam cada pedido (um por poll do outbox).
    for noisy in ("httpx", "httpcore", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    if (os.getenv("AXIOM_TOKEN") or "").strip():
        _start_axiom(root)


_axiom_listener: QueueListener | None = None


def _start_axiom(root: logging.Logger) -> None:
    """O envio para o Axiom é HTTP síncrono: corre numa thread própria.

    Antes corria dentro da chamada de log, no event loop, e bloqueava todos os
    pedidos em curso durante o envio (até 5 s).
    """
    global _axiom_listener
    if _axiom_listener is not None:
        return
    from core.log_safe import RedactSecretsFilter

    ax = AxiomHandler()
    ax.setLevel(logging.INFO)
    q: queue.SimpleQueue = queue.SimpleQueue()
    handler = QueueHandler(q)
    handler.setLevel(logging.INFO)
    handler.addFilter(RedactSecretsFilter())  # todos os loggers, não só os nomeados
    _axiom_listener = QueueListener(q, ax)
    _axiom_listener.start()
    # No SIGTERM (deploy/restart) envia o que ficou na fila em vez de o perder.
    listener = _axiom_listener
    atexit.register(lambda: listener._thread is not None and listener.stop())
    root.addHandler(handler)
