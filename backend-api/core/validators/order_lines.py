"""Validação de linhas de orçamento/encomenda — esquema unificado (1 query, não
13 — antes havia um round-trip por família de catálogo para o mesmo EAN)."""
from __future__ import annotations

from fastapi import HTTPException

from core.cqrs.queries.assentos_catalog import assento_model_detail
from core.database import get_db
from models.catalog_registry import storefront_mode_for_tipo


def _load_products_by_ean(eans: list[str]) -> tuple[dict[str, dict], dict[str, str]]:
    """Mapa EAN → row (+ categoria via modelo) + EAN → tipo_catalogo."""
    if not eans:
        return {}, {}
    res = (
        get_db()
        .table("product_variants")
        .select(
            "ean, id_modelo, tipo_catalogo, attributes, "
            "product_models(id_categoria, categories(carrinho_step, carrinho_min))"
        )
        .in_("ean", eans)
        .execute()
    )
    by_ean: dict[str, dict] = {}
    product_tipo: dict[str, str] = {}
    for row in res.data or []:
        modelo = row.get("product_models") or {}
        if isinstance(modelo, list) and modelo:
            modelo = modelo[0]
        if not isinstance(modelo, dict):
            modelo = {}
        row = dict(row)
        row["categories"] = modelo.get("categories") or {}
        row["id_categoria"] = modelo.get("id_categoria")
        row["altura"] = (row.get("attributes") or {}).get("altura")
        by_ean[row["ean"]] = row
        product_tipo[row["ean"]] = row.get("tipo_catalogo")
    return by_ean, product_tipo


def _valid_model_colors(model_ids: list[str]) -> set[tuple[str, int]]:
    if not model_ids:
        return set()
    res = (
        get_db()
        .table("product_model_colors")
        .select("id_modelo, numero")
        .in_("id_modelo", model_ids)
        .execute()
    )
    return {(str(c["id_modelo"]), int(c["numero"])) for c in (res.data or [])}


def validate_order_lines(linhas) -> None:
    """Valida EAN, quantidade, cor e (assentos) altura."""
    eans = list({l.ean for l in linhas})
    by_ean, product_tipo = _load_products_by_ean(eans)

    non_assento_model_ids = list(
        {
            str(r["id_modelo"])
            for e, r in by_ean.items()
            if storefront_mode_for_tipo(product_tipo.get(e)) != "assento" and r.get("id_modelo")
        }
    )
    valid_colors = _valid_model_colors(non_assento_model_ids)

    assento_details: dict[str, dict] = {}
    for ean, row in by_ean.items():
        if storefront_mode_for_tipo(product_tipo.get(ean)) != "assento":
            continue
        mid = str(row.get("id_modelo") or "")
        if mid and mid not in assento_details:
            assento_details[mid] = assento_model_detail(mid) or {}

    for linha in linhas:
        row = by_ean.get(linha.ean)
        if not row:
            raise HTTPException(status_code=400, detail=f"EAN desconhecido: {linha.ean}")

        cat = row.get("categories") or {}
        if isinstance(cat, list) and cat:
            cat = cat[0]
        if not isinstance(cat, dict):
            cat = {}
        step = cat.get("carrinho_step") or 6
        min_q = cat.get("carrinho_min") or step
        if step and linha.quantidade % step != 0:
            raise HTTPException(status_code=400, detail=f"Quantidade para {linha.ean} deve ser múltiplo de {step}.")
        if min_q and linha.quantidade < min_q:
            raise HTTPException(status_code=400, detail=f"Quantidade mínima para {linha.ean} é {min_q}.")

        tipo = product_tipo.get(linha.ean, "almofada")
        id_modelo = str(row.get("id_modelo") or "")

        if storefront_mode_for_tipo(tipo) == "assento":
            altura = (getattr(linha, "altura", None) or "").strip()
            if not altura:
                raise HTTPException(status_code=400, detail=f"Indique a altura para o assento {linha.ean}.")
            detail = assento_details.get(id_modelo) or {}
            product_altura = (row.get("altura") or "").strip()
            if product_altura:
                if altura != product_altura:
                    raise HTTPException(status_code=400, detail=f"Altura «{altura}» não corresponde ao EAN {linha.ean}.")
            else:
                alturas = detail.get("alturas") or []
                if altura not in alturas:
                    raise HTTPException(status_code=400, detail=f"Altura «{altura}» inválida para este modelo.")
            valid_cors = {
                int(c.get("numero", 0)) for c in (detail.get("modelo_cores") or []) if c.get("visibilidade", True)
            }
            if valid_cors and int(linha.numero_cor) not in valid_cors:
                raise HTTPException(status_code=400, detail=f"Cor n. {linha.numero_cor} inválida para este EAN.")
        elif id_modelo and (id_modelo, linha.numero_cor) not in valid_colors:
            raise HTTPException(status_code=400, detail=f"Cor n. {linha.numero_cor} inválida para este EAN.")
