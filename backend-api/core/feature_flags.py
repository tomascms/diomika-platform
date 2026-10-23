"""Feature flags simples via env — FEATURE_<NOME>=1|0.

Exemplos:
  FEATURE_CONTACT_FORM=1
  FEATURE_ANALYTICS=1
  FEATURE_MAINTENANCE_BANNER=0
"""
from __future__ import annotations

import os


def flag(name: str, default: bool = False) -> bool:
    key = f"FEATURE_{(name or '').strip().upper()}"
    raw = os.getenv(key)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def flags_snapshot() -> dict[str, bool]:
    """Flags conhecidas (para /health/detail ops)."""
    known = (
        "CONTACT_FORM",
        "ORCAMENTO_FORM",
        "MAINTENANCE_BANNER",
        "CATALOG_WRITE",
    )
    return {k: flag(k, default=True) for k in known}
