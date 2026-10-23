"""Queries — catálogo de assentos (detalhe de modelo para encomendas).

Esquema unificado: 1 tabela de modelos, 1 de variantes, 1 de cores — já não
há tabelas "modelos_assentos"/"assento"/"modelo_assento_cores" próprias."""
from __future__ import annotations

from core.database import get_db
from core.visibility import is_visible


def _modelo_cores(data: dict) -> list[dict]:
    cores = [c for c in (data.get("modelo_cores") or []) if c.get("visibilidade", True)]
    cores.sort(key=lambda c: c.get("numero", 0))
    return cores


def _attach_cores(rows: list[dict]) -> None:
    if not rows:
        return
    db = get_db()
    model_ids = [str(r["id"]) for r in rows if r.get("id")]
    by_model: dict[str, list] = {mid: [] for mid in model_ids}
    if model_ids:
        for cor in (
            db.table("product_model_colors")
            .select("id_modelo, numero, nome, imagem, visibilidade")
            .in_("id_modelo", model_ids)
            .execute()
            .data
            or []
        ):
            mid = str(cor.get("id_modelo") or "")
            if mid in by_model:
                by_model[mid].append(cor)
    for row in rows:
        row["modelo_cores"] = _modelo_cores({"modelo_cores": by_model.get(str(row.get("id") or ""), [])})


def assento_model_detail(id_modelo: str):
    db = get_db()
    res = (
        db.table("product_models")
        .select("*, categories(*), product_variants(*)")
        .eq("id", id_modelo)
        .eq("tipo_catalogo", "assento")
        .single()
        .execute()
    )
    data = res.data
    if not data:
        return None
    if not is_visible(data):
        return None
    _attach_cores([data])
    variant_rows = [
        v
        for v in (data.get("product_variants") or [])
        if v.get("visibilidade", True) and str(v.get("ean") or "").strip()
    ]
    variant_rows.sort(key=lambda v: str((v.get("attributes") or {}).get("altura") or ""))
    data["assento"] = variant_rows
    data["modelo_cores"] = _modelo_cores(data)
    if not variant_rows or not data["modelo_cores"]:
        return None
    alturas = (data.get("attributes") or {}).get("alturas") or []
    data["alturas"] = sorted(alturas)
    return data
