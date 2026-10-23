"""Endpoints administrativos: export, import, infra."""
from __future__ import annotations

import asyncio
import csv
import io
import json

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from core.audit import audit_request
from core.auth import assert_table_action, require_admin
from core.database import get_db
from core.local_only import admin_must_be_local
from models.schemas import TABLE_MAP

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(admin_must_be_local), Depends(require_admin)],
)

CATALOG_EXPORTABLE = {
    "categories",
    "pedidos_orcamento",
    "encomendas_internas",
    "contact_messages",
}


def _exportable_tables() -> set[str]:
    from models.catalog_registry import all_colors_tables, all_model_tables, all_product_tables

    return CATALOG_EXPORTABLE | set(all_model_tables()) | set(all_product_tables()) | set(all_colors_tables())


def _schema_for(table_name: str):
    cfg = TABLE_MAP.get(table_name)
    if not cfg or not cfg.get("schema"):
        raise HTTPException(
            status_code=404,
            detail=f"Tabela «{table_name}» não registada no catálogo",
        )
    return cfg["schema"]


def _normalize_row(row: dict) -> dict:
    out = {}
    for key, val in row.items():
        if val is None or val == "":
            continue
        if isinstance(val, str):
            stripped = val.strip()
            if stripped.startswith(("{", "[")):
                try:
                    out[key] = json.loads(stripped)
                    continue
                except json.JSONDecodeError:
                    pass
            out[key] = stripped
        else:
            out[key] = val
    return out


@router.get("/export/{table_name}")
def export_csv(request: Request, table_name: str):
    from models.catalog_registry import level_for_table, physical_table_for, tipo_for_table

    exportable = _exportable_tables()
    if table_name not in exportable:
        raise HTTPException(status_code=404, detail="Categoria não exportável")
    role = getattr(request.state, "api_role", "admin")
    assert_table_action(table_name, "read", role)

    query = get_db().table(physical_table_for(table_name)).select("*")
    tipo = tipo_for_table(table_name)
    if tipo and level_for_table(table_name) == "colors":
        # product_model_colors não tem `tipo_catalogo` — a família vem do
        # modelo-pai, por isso filtra-se pelo embed (ver admin_crud._scoped_list).
        query = get_db().table(physical_table_for(table_name)).select(
            "*, product_models!inner(tipo_catalogo)"
        ).eq("product_models.tipo_catalogo", tipo)
    elif tipo:
        query = query.eq("tipo_catalogo", tipo)
    rows = query.order("created_at", desc=True).execute().data or []
    audit_request(request, action="export", resource=table_name, detail={"rows": len(rows)})
    if not rows:
        return StreamingResponse(
            iter(["id\n"]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={table_name}.csv"},
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        flat = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()}
        writer.writerow(flat)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table_name}.csv"},
    )


@router.post("/import/{table_name}")
async def import_csv(
    request: Request,
    table_name: str,
    file: UploadFile = File(...),
    dry_run: bool = False,
):
    """Importa CSV — valida via schema Pydantic; upsert por id quando presente."""
    from models.catalog_registry import fold_attributes, physical_table_for, tipo_for_table

    exportable = _exportable_tables()
    if table_name not in exportable:
        raise HTTPException(status_code=404, detail="Categoria não importável")
    if table_name in {"pedidos_orcamento", "encomendas_internas", "contact_messages"}:
        raise HTTPException(status_code=400, detail="Importação não permitida para esta tabela")
    role = getattr(request.state, "api_role", "admin")
    assert_table_action(table_name, "create", role)
    physical_table = physical_table_for(table_name)
    tipo = tipo_for_table(table_name)

    schema = _schema_for(table_name)
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ficheiro demasiado grande (máx. 5 MB)")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Ficheiro deve ser UTF-8") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV vazio ou sem cabeçalho")

    db = get_db()
    created = updated = skipped = 0
    errors: list[str] = []

    for idx, row in enumerate(reader, start=2):
        payload = _normalize_row(row)
        if not payload:
            skipped += 1
            continue
        record_id = payload.pop("id", None)
        payload = fold_attributes(table_name, payload)
        if tipo:
            payload["tipo_catalogo"] = tipo
        try:
            validated = schema.model_validate(payload)
            data = validated.model_dump(mode="json")
            for k, v in list(data.items()):
                if isinstance(v, str) and v == "":
                    data[k] = None
        except ValidationError as exc:
            errors.append(f"Linha {idx}: {exc.errors()[0]['msg']}")
            continue

        if dry_run:
            created += 1
            continue

        try:
            # Fora do event loop: uma chamada por linha bloquearia a API durante a importação toda.
            if record_id:
                await asyncio.to_thread(lambda: db.table(physical_table).update(data).eq("id", record_id).execute())
                updated += 1
            else:
                await asyncio.to_thread(lambda: db.table(physical_table).insert(data).execute())
                created += 1
        except Exception as exc:
            errors.append(f"Linha {idx}: {str(exc)[:120]}")

    if errors and not dry_run and created == 0 and updated == 0:
        raise HTTPException(status_code=400, detail={"message": "Importação falhou", "errors": errors[:20]})

    if not dry_run and (created or updated):
        # Sem isto os registos importados só apareciam na loja quando a cache expirasse.
        from core.cache import invalidate_catalog_change

        invalidate_catalog_change()

    audit_request(
        request,
        action="import",
        resource=table_name,
        detail={"dry_run": dry_run, "created": created, "updated": updated, "errors": len(errors)},
    )
    return {
        "status": "ok",
        "dry_run": dry_run,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:20],
    }
