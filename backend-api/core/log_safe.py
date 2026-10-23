"""Filtro de logging — evita secrets e emails em stdout/ficheiros."""
from __future__ import annotations

import logging
import re

_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?secret[_-]?key|api[_-]?ops[_-]?key|authorization|bearer)\s*[:=]\s*\S+"), r"\1=[redacted]"),
    (re.compile(r"(?i)(password|passwd|secret|token|service_role|supabase[_-]?key|smtp[_-]?pass(word)?)\s*[:=]\s*\S+"), r"\1=[redacted]"),
    (re.compile(r"(?i)(cookie|set-cookie)\s*[:=]\s*\S+"), r"\1=[redacted]"),
    (re.compile(r"(?i)(eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,})"), "[redacted-jwt]"),
    (re.compile(r"(dms1\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)"), "[redacted-session]"),
    (re.compile(r"(?i)(sb_secret_|sb_publishable_|cfat_)[A-Za-z0-9._\-/+=]+"), "[redacted-key]"),
    # Emails (RGPD): t***@dominio.pt — o domínio fica para diagnóstico.
    (re.compile(r"\b([A-Za-z0-9])[A-Za-z0-9._%+-]*@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})\b"), r"\1***@\2"),
]


def redact_text(text: str) -> str:
    out = text
    for pattern, repl in _PATTERNS:
        out = pattern.sub(repl, out)
    return out


class RedactSecretsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = redact_text(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: redact_text(str(v)) if isinstance(v, str) else v for k, v in record.args.items()}
                elif isinstance(record.args, tuple):
                    record.args = tuple(
                        redact_text(a) if isinstance(a, str) else a for a in record.args
                    )
        except Exception:
            pass
        return True


def install_log_redaction() -> None:
    filt = RedactSecretsFilter()
    root = logging.getLogger()
    if not any(isinstance(f, RedactSecretsFilter) for f in root.filters):
        root.addFilter(filt)
    for name in ("diomika-api", "diomika-audit", "uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).addFilter(filt)
