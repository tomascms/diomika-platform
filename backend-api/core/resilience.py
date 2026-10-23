"""Resiliência: DLQ, retries, circuit breaker, idempotência."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("diomika-resilience")

_file_handler = logging.FileHandler(LOG_DIR / "api_consistency.log", encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
if not logger.handlers:
    logger.addHandler(_file_handler)
    logger.setLevel(logging.INFO)

DLQ_FILE = LOG_DIR / "dlq_events.jsonl"


def log_dlq_event(operation: str, identifier: str, error: str | Exception) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "identifier": identifier,
        "error": str(error),
    }
    logger.error("DLQ_EVENT | %s | ID: %s | Error: %s", operation, identifier, error)
    with DLQ_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_idempotency(operation: str, identifier: str) -> None:
    logger.info("IDEMPOTENCY_HIT | %s | ID: %s", operation, identifier)


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    failures: int = 0
    opened_at: float | None = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if time.time() - self.opened_at >= self.recovery_timeout:
            self.failures = 0
            self.opened_at = None
            logger.info("CircuitBreaker %s: half-open/recovered", self.name)
            return True
        return False

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.time()
            logger.error("CircuitBreaker %s: OPEN after %s failures", self.name, self.failures)


_smtp_breaker = CircuitBreaker("smtp")


def get_smtp_breaker() -> CircuitBreaker:
    return _smtp_breaker


async def async_retry_with_backoff(
    fn: Callable[..., Any],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    operation: str = "operation",
    breaker: CircuitBreaker | None = None,
):
    import asyncio

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        if breaker and not breaker.allow():
            raise RuntimeError(f"Circuit breaker aberto: {breaker.name}")
        try:
            result = await fn()
            if breaker:
                breaker.record_success()
            return result
        except Exception as exc:
            last_error = exc
            if breaker:
                breaker.record_failure()
            if attempt >= max_attempts:
                break
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning("%s tentativa %s/%s falhou: %s", operation, attempt, max_attempts, exc)
            await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error
