"""Descrição de formulário de uma tabela do backoffice.

Separado da rota (/system/schema/form/{table}) para o formulário agregado
(routes/admin_form.py) poder devolver o schema junto com os dados, numa só
resposta, em vez de obrigar o backoffice a uma chamada por peça.
"""
from __future__ import annotations

from fastapi import HTTPException

from core.auth import CRUD_INFRA_BLOCKED
from models.schemas import TABLE_MAP
from models.ui_schema import get_form_fields


def build_form_schema(table_name: str) -> dict:
    if table_name not in TABLE_MAP or table_name in CRUD_INFRA_BLOCKED:
        raise HTTPException(
            status_code=404,
            detail=f"Tabela «{table_name}» não registada no catálogo",
        )
    cfg = TABLE_MAP[table_name]
    schema = cfg.get("schema")
    if not schema:
        raise HTTPException(status_code=404, detail="Sem schema")
    # Não expor metadados internos/callable
    safe_config = {
        k: v
        for k, v in cfg.items()
        if k != "schema" and not callable(v) and not str(k).startswith("_")
    }
    return {
        "table": table_name,
        "label": cfg.get("label", table_name),
        "fields": get_form_fields(schema, cfg, table_name),
        "config": safe_config,
    }
