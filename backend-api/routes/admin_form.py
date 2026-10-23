"""Tudo o que um formulário do backoffice precisa, numa só resposta.

Abrir um registo custava 3 a 4 idas ao servidor — a lista de categorias
(bloqueante, antes de tudo o resto), o schema, o registo, e mais uma por cada
tabela relacionada — e uma quinta ao escolher o modelo. Sobre um túnel
Cloudflare até uma VM pequena, essa latência soma-se de forma bem visível.
Aqui tudo isso é montado do lado do servidor e volta de uma vez.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from core.admin_form_schema import build_form_schema
from core.auth import assert_table_action, require_admin
from core.local_only import admin_must_be_local
from models.catalog_registry import tipo_for_table, product_table_for_tipo, colors_table_for_tipo
from routes.admin_crud import _db_table, _scoped, relation_options
from models.catalog_registry import list_select_query

logger = logging.getLogger("diomika-api")

router = APIRouter(
    prefix="/admin/form",
    tags=["Admin Form"],
    dependencies=[Depends(admin_must_be_local), Depends(require_admin)],
)

# Campos de modelo que alimentam o picker da variante (dimensão/altura).
_DISCRIMINATOR_BY_WIDGET = {
    "dimensao_modelo": ("dimensoes", "dimensoes_modelo"),
    "altura_modelo": ("alturas", "altura_modelo"),
}


def _role(request: Request) -> str:
    return getattr(request.state, "api_role", "admin")


def _discriminator_options(fields: list[dict], id_modelo: str | None) -> dict[str, list[str]]:
    """Valores que o modelo-pai permite para o campo discriminador da variante.
    Vêm de `attributes` do modelo — o backoffice lia-os do nível de topo, onde
    já não estão."""
    if not id_modelo:
        return {}
    widget = next(
        (f["widget"] for f in fields if f.get("widget") in _DISCRIMINATOR_BY_WIDGET),
        None,
    )
    if not widget:
        return {}
    attr_name, option_key = _DISCRIMINATOR_BY_WIDGET[widget]

    model_table = next(
        (f["relation"] for f in fields if f.get("name") == "id_modelo" and f.get("relation")),
        None,
    )
    if not model_table:
        return {}
    try:
        res = (
            _scoped(_db_table(model_table).select("attributes"), model_table)
            .eq("id", id_modelo)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning("Opções do discriminador falharam para modelo %s", id_modelo)
        return {}
    rows = res.data or []
    raw = ((rows[0] if rows else {}).get("attributes") or {}).get(attr_name)
    values = [str(v).strip() for v in raw if str(v).strip()] if isinstance(raw, list) else []
    return {option_key: values}


@router.get("/{table_name}")
def form_bundle(
    request: Request,
    table_name: str,
    id: str | None = None,
):
    """Schema + registo + opções de relação + categorias, de uma só vez."""
    schema = build_form_schema(table_name)
    role = _role(request)
    assert_table_action(table_name, "read", role)

    fields = schema.get("fields") or []

    record = None
    if id:
        res = (
            _scoped(_db_table(table_name).select(list_select_query(table_name)), table_name)
            .eq("id", id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Registo não encontrado")
        record = res.data[0]

    relations: dict[str, list[dict]] = {}
    for rel_table in {f["relation"] for f in fields if f.get("relation")}:
        try:
            assert_table_action(rel_table, "read", role)
        except HTTPException:
            relations[rel_table] = []
            continue
        try:
            relations[rel_table] = relation_options(rel_table, limit=200)
        except Exception:
            # Uma relação indisponível não deve impedir o formulário de abrir.
            logger.warning("Opções de relação falharam para %s", rel_table)
            relations[rel_table] = []

    categories = relations.get("categories")
    if categories is None:
        try:
            categories = relation_options("categories", limit=300)
        except Exception:
            categories = []

    tipo = tipo_for_table(table_name)
    return {
        **schema,
        "record": record,
        "relations": relations,
        "categories": [c for c in categories if c.get("tipo_catalogo")],
        "field_options": _discriminator_options(fields, (record or {}).get("id_modelo") or None),
        "tipo_catalogo": tipo,
        "product_table": product_table_for_tipo(tipo),
        "colors_table": colors_table_for_tipo(tipo),
    }
