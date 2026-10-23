"""Comandos CQRS — soft-delete genérico.

Criação/edição de categorias, modelos, produtos e cores: usar admin_crud
(TABLE_MAP + validação Pydantic) — é CRUD real, não precisa de um comando
dedicado por tabela.
"""
from __future__ import annotations

from fastapi import HTTPException

from core.database import get_db


def soft_delete(table: str, record_id: str) -> dict:
    from models.catalog_registry import physical_table_for

    db = get_db()
    res = db.table(physical_table_for(table)).update({"visibilidade": False}).eq("id", record_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Registo não encontrado")
    return {"status": "soft_deleted", "id": record_id}
