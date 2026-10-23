"""Tudo o que um formulário do backoffice precisa, numa só resposta.

Abrir um registo custava 3 a 4 idas ao servidor — a lista de categorias
(bloqueante, antes de tudo o resto), o schema, o registo, e mais uma por cada
tabela relacionada — e uma quinta ao escolher o modelo. Sobre um túnel
Cloudflare até uma VM pequena, essa latência soma-se de forma bem visível.
Aqui tudo isso é montado do lado do servidor e volta de uma vez, com as consultas em
paralelo (cada uma custa ~150 ms entre a VM e a BD) e, num modelo, já com as cores e os
produtos (EAN) — o formulário abria e só depois pedia essas duas listas.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, Request

from core.admin_form_schema import build_form_schema
from core.auth import assert_table_action, require_admin
from core.local_only import admin_must_be_local
from models.catalog_registry import tipo_for_table, product_table_for_tipo, colors_table_for_tipo
from routes.admin_crud import _db_table, _scoped, admin_list_rows, relation_options
from models.catalog_registry import all_model_tables, list_select_query

logger = logging.getLogger("diomika-api")

router = APIRouter(
    prefix="/admin/form",
    tags=["Admin Form"],
    dependencies=[Depends(admin_must_be_local), Depends(require_admin)],
)

_POOL = ThreadPoolExecutor(max_workers=6, thread_name_prefix="form-bundle")

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
    """Schema + registo + opções de relação + categorias (+ cores e EAN de um modelo), de uma só vez."""
    schema = build_form_schema(table_name)
    role = _role(request)
    assert_table_action(table_name, "read", role)
    fields = schema.get("fields") or []
    tipo = tipo_for_table(table_name)
    product_table = product_table_for_tipo(tipo)
    colors_table = colors_table_for_tipo(tipo)

    def _record():
        res = (
            _scoped(_db_table(table_name).select(list_select_query(table_name)), table_name)
            .eq("id", id)
            .execute()
        )
        return res.data[0] if res.data else None

    def _readable(table: str) -> bool:
        try:
            assert_table_action(table, "read", role)
            return True
        except HTTPException:
            return False

    rel_tables = {f["relation"] for f in fields if f.get("relation")}
    jobs = {}
    if id:
        jobs["record"] = _POOL.submit(_record)
    for rel in rel_tables:
        if _readable(rel):
            jobs[("rel", rel)] = _POOL.submit(relation_options, rel, limit=200)
    if "categories" not in rel_tables:
        jobs["categories"] = _POOL.submit(relation_options, "categories", limit=300)
    with_children = bool(id) and table_name in all_model_tables() and product_table and colors_table
    if with_children and _readable(colors_table) and _readable(product_table):
        jobs["colors"] = _POOL.submit(admin_list_rows, colors_table, id_modelo=id, limit=200)
        jobs["variants"] = _POOL.submit(admin_list_rows, product_table, id_modelo=id, limit=100)

    results = {}
    for key, fut in jobs.items():
        try:
            results[key] = fut.result()
        except Exception:
            if key == "record":
                raise
            # Uma relação/lista indisponível não deve impedir o formulário de abrir.
            logger.warning("Formulário %s: %s falhou", table_name, key, exc_info=True)
            results[key] = None

    record = results.get("record")
    if id and not record:
        raise HTTPException(status_code=404, detail="Registo não encontrado")
    relations = {rel: results.get(("rel", rel)) or [] for rel in rel_tables}
    categories = relations.get("categories") if "categories" in rel_tables else results.get("categories") or []

    bundle = {
        **schema,
        "record": record,
        "relations": relations,
        "categories": [c for c in categories if c.get("tipo_catalogo")],
        "field_options": _discriminator_options(fields, (record or {}).get("id_modelo") or None),
        "tipo_catalogo": tipo,
        "product_table": product_table,
        "colors_table": colors_table,
    }
    if "colors" in jobs:
        bundle["children"] = {
            "colors": results.get("colors"),
            "variants": results.get("variants"),
            # Campos da variante (o painel de EAN precisa do atributo extra, ex. dimensões).
            "variant_fields": build_form_schema(product_table).get("fields") or [],
        }
    return bundle
