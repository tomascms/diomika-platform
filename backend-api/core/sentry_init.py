"""Sentry opcional — só activa com SENTRY_DSN."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("diomika-sentry")


def init_sentry() -> bool:
    dsn = (os.getenv("SENTRY_DSN") or "").strip()
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning("SENTRY_DSN definido mas sentry-sdk não instalado")
        return False

    env = (os.getenv("DIOMIKA_ENV") or "development").strip().lower()
    sample = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE") or ("0.05" if env == "production" else "0.0"))
    # Só ERROR+; WARNING IMAP/health não devem criar issues
    logging_integration = LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
    sentry_sdk.init(
        dsn=dsn,
        environment=env,
        traces_sample_rate=max(0.0, min(1.0, sample)),
        send_default_pii=False,
        ignore_errors=[
            KeyboardInterrupt,
            SystemExit,
        ],
        before_send=_before_send,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
            logging_integration,
        ],
    )
    logger.info("Sentry activo (env=%s, traces=%.2f)", env, sample)
    return True


def _transaction_name(event: dict) -> str:
    tx = event.get("transaction") or ""
    req = (event.get("request") or {}).get("url") or ""
    return f"{tx} {req}".lower()


_IGNORE_ERRORS = {
    "health_check_keywords": ("/health", "health_ready", "health_check"),
    "db_conflict_keywords": ("duplicate key", "23505", "já existe"),
    "postgrest_keywords": ("pgrst200", "could not find a relationship"),
    "email_transient_keywords": ("socket error", "eof", "imap", "socket", "fetch", "broken pipe", "imap ligação perdida"),
    "bootstrap_keywords": ("redis_url", "obrigat", "required"),
}


def _matches_any(text: str, keywords: tuple) -> bool:
    """Check if any keyword appears in text."""
    return any(kw in text for kw in keywords)


def _before_send(event, hint):
    """Filtra ruído operacional que não é bug de código."""
    tx = _transaction_name(event)
    log_entry = event.get("logentry") or {}
    message = (log_entry.get("message") or event.get("message") or "").lower()
    exc_info = hint.get("exc_info") if hint else None
    exc_name = ""
    msg = ""
    status = None
    if exc_info and len(exc_info) >= 2:
        exc = exc_info[1]
        exc_name = type(exc).__name__
        msg = str(exc).lower()
        status = getattr(exc, "status_code", None)

    # Health checks — não é bug
    if _matches_any(tx, _IGNORE_ERRORS["health_check_keywords"]):
        return None
    if status == 503 and _matches_any(msg, ("degraded", "database")):
        return None

    # HTTP 4xx esperados
    if exc_name == "HTTPException" and status and 400 <= int(status) < 500:
        return None

    # Conflitos DB
    if _matches_any(msg, _IGNORE_ERRORS["db_conflict_keywords"]):
        return None
    if _matches_any(message, _IGNORE_ERRORS["db_conflict_keywords"]):
        return None
    if _matches_any(msg, _IGNORE_ERRORS["postgrest_keywords"]):
        return None
    if _matches_any(message, _IGNORE_ERRORS["postgrest_keywords"]):
        return None

    # Email transitório
    if "socket error" in msg or ("eof" in msg and _matches_any(msg, ("imap", "socket", "fetch"))):
        return None
    if _matches_any(message, ("imap ligação perdida",)):
        return None
    if "erro ao processar email" in message and _matches_any(message, ("socket", "eof", "fetch", "broken pipe")):
        return None

    # Bootstrap config
    if "redis_url" in msg and _matches_any(msg, ("obrigat", "required")):
        return None

    return event
