"""Gravação atómica de um modelo com as suas cores e variantes (API-08).

O backoffice enviava 1 pedido por modelo, por cor e por EAN; uma falha a meio deixava o catálogo a meio.
Aqui valida-se tudo com os mesmos esquemas do CRUD e a gravação é uma só chamada `rpc("save_model_bundle")`,
uma só transacção na BD (db/migrations/2026-11-02_catalogue_functions.sql).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError

from core.database import get_db
from models.catalog_registry import (
    colors_schema_for_tipo,
    fold_attributes,
    product_schema_for_tipo,
    tipo_for_table,
)
from models.schemas import TABLE_MAP


def _validated(schema, row: dict) -> dict:
    """O mesmo esquema do CRUD; a mensagem é a do primeiro erro, não o despejo do pydantic."""
    try:
        return _plain(schema(**row).model_dump())
    except ValidationError as exc:
        err = exc.errors()[0]
        field = ".".join(str(p) for p in err.get("loc", ()))
        raise ValueError(f"{field + ': ' if field else ''}{err['msg'].removeprefix('Value error, ')}") from exc


def _plain(payload: dict) -> dict:
    return {k: str(v) if isinstance(v, UUID) else v for k, v in payload.items()}


def _uuid_list(values: Any, field: str) -> list[str]:
    if values in (None, []):
        return []
    if not isinstance(values, list):
        raise ValueError(f"«{field}» tem de ser uma lista.")
    try:
        return [str(UUID(str(v))) for v in values]
    except ValueError as exc:
        raise ValueError(f"«{field}» tem identificadores inválidos.") from exc


def _assert_publishable(model_id: str, colors: list[dict], variants: list[dict], del_colors: list[str], del_variants: list[str]) -> None:
    """Para publicar: pelo menos uma cor com imagem e um produto com EAN, contando o que já lá está (menos o que sai)."""
    db = get_db()
    in_payload_colors = {c["id"] for c in colors}
    in_payload_variants = {v["id"] for v in variants}
    kept_colors = [
        c
        for c in (db.table("product_model_colors").select("id,imagem").eq("id_modelo", model_id).execute().data or [])
        if c["id"] not in del_colors and c["id"] not in in_payload_colors
    ]
    kept_variants = [
        v
        for v in (db.table("product_variants").select("id,ean").eq("id_modelo", model_id).execute().data or [])
        if v["id"] not in del_variants and v["id"] not in in_payload_variants
    ]
    if not any(str(c.get("imagem") or "").strip() for c in colors + kept_colors):
        raise ValueError("Adicione pelo menos uma cor com imagem antes de publicar na loja.")
    if not any(str(v.get("ean") or "").strip() for v in variants + kept_variants):
        raise ValueError("Adicione pelo menos um produto com EAN antes de publicar na loja.")


def _assert_children_belong(model_id: str, colors: list[dict], variants: list[dict], del_colors: list[str], del_variants: list[str]) -> None:
    """Cada id de cor/variante (a gravar ou a apagar) é novo ou já é deste modelo: o upsert por id reatribuía
    linhas de outro modelo, e o apagar por lista tocava em linhas alheias."""
    db = get_db()
    for table, ids in (
        ("product_model_colors", [c["id"] for c in colors] + del_colors),
        ("product_variants", [v["id"] for v in variants] + del_variants),
    ):
        if not ids:
            continue
        rows = db.table(table).select("id,id_modelo").in_("id", ids).execute().data or []
        if any(str(r.get("id_modelo")) != model_id for r in rows):
            raise ValueError("Há cores ou produtos que pertencem a outro modelo.")


def build_bundle(table_name: str, body: dict) -> tuple[dict, dict]:
    """Valida o corpo e devolve (parâmetro do rpc, linha do modelo). ValueError com texto para o utilizador."""
    tipo = tipo_for_table(table_name)
    model_schema = TABLE_MAP.get(table_name, {}).get("schema")
    colors_schema = colors_schema_for_tipo(tipo)
    variant_schema = product_schema_for_tipo(tipo)
    if not (tipo and model_schema and colors_schema and variant_schema):
        raise ValueError("Esta tabela não é um modelo de catálogo.")
    if not isinstance(body.get("model"), dict):
        raise ValueError("Falta o modelo.")

    model_in = fold_attributes(table_name, dict(body["model"]))
    model_in["id"] = str(model_in.get("id") or uuid4())
    model_in["tipo_catalogo"] = tipo  # a família é a da tabela, nunca a do corpo do pedido
    model = _validated(model_schema, model_in)
    visible = bool(model.get("visibilidade"))

    colors: list[dict] = []
    for raw in body.get("colors") or []:
        row = dict(raw)
        row["id"] = str(row.get("id") or uuid4())
        row["id_modelo"] = model["id"]
        row = _validated(colors_schema, row)
        if visible:
            row["visibilidade"] = True  # publicar o modelo publica o que é dele (como o /publish)
        colors.append(row)

    variants: list[dict] = []
    for raw in body.get("variants") or []:
        row = dict(raw)
        row["id"] = str(row.get("id") or uuid4())
        row["id_modelo"] = model["id"]
        row["tipo_catalogo"] = tipo
        row = _validated(variant_schema, row)
        if visible:
            row["visibilidade"] = True
        variants.append(row)

    del_colors = _uuid_list(body.get("delete_colors"), "delete_colors")
    del_variants = _uuid_list(body.get("delete_variants"), "delete_variants")
    _assert_children_belong(model["id"], colors, variants, del_colors, del_variants)
    if visible:
        _assert_publishable(model["id"], colors, variants, del_colors, del_variants)

    param = {
        "model": model,
        "colors": colors,
        "variants": variants,
        "delete_colors": del_colors,
        "delete_variants": del_variants,
    }
    return param, model


def save_bundle(param: dict) -> dict:
    """Uma só transacção; qualquer erro (EAN repetido, FK, restrição) deixa tudo como estava."""
    res = get_db().rpc("save_model_bundle", {"p": param}).execute()
    return res.data or {}
