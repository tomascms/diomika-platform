"""Helpers — catálogo público só com visibilidade=true."""
from __future__ import annotations

from fastapi import HTTPException


def is_visible(record: dict | None) -> bool:
    if not record:
        return False
    return record.get("visibilidade", True) is not False


def require_visible(record: dict | None, *, detail: str = "Registo não encontrado") -> dict:
    if not is_visible(record):
        raise HTTPException(status_code=404, detail=detail)
    return record
