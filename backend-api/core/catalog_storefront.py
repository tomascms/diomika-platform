"""Queries genéricas de catálogo para a loja — esquema unificado.

3 tabelas físicas para todas as categorias (product_models, product_variants,
product_model_colors); os campos que variavam por família (dimensoes, altura,
segmento, ...) vivem agora em `attributes` (jsonb) em vez de serem colunas
próprias de 13 tabelas — por isso já não há um lookup de "qual é a tabela de
cores desta família" nem um loop sobre 13 tabelas para encontrar um EAN.
"""

from __future__ import annotations

import re

from core.database import get_db
from core.visibility import is_visible
from models.catalog_registry import CATALOG_TYPES, is_valid_tipo
from models.schemas import PRODUCT_MODEL_COLORS_TABLE, PRODUCT_MODELS_TABLE, PRODUCT_VARIANTS_TABLE
from models.storefront_meta import attach_storefront_fields, storefront_context_for_tipo

# A loja ainda não tem "ver mais": nenhum chamador envia `limit`, por isso o
# valor por omissão é o tamanho real da página que o cliente vê. Com 24 uma
# categoria com mais do que 24 modelos visíveis perdia os restantes sem
# qualquer aviso. Mantém-se um limite (a query continua limitada) mas acima de
# qualquer categoria plausível deste catálogo — a maior tem 10 modelos.
DEFAULT_PAGE_LIMIT = 200
MAX_PAGE_LIMIT = 500


def _has_ean(row: dict | None) -> bool:
    return bool(str((row or {}).get("ean") or "").strip())


def _visible_products(rows: list[dict] | None) -> list[dict]:
    """Produtos publicáveis: visíveis e com EAN (sem EAN não entram na loja)."""
    return [row for row in (rows or []) if is_visible(row) and _has_ean(row)]


def _modelo_cores(data: dict) -> list[dict]:
    cores = [c for c in (data.get("modelo_cores") or []) if is_visible(c)]
    cores.sort(key=lambda c: c.get("numero", 0))
    return cores


def _product_select_fields() -> str:
    return "id, ean, barcode_url, visibilidade, attributes"


def _category_select() -> str:
    return "id, nome, carrinho_step, carrinho_min, slug, tipo_catalogo"


def _attach_modelo_cores(rows: list[dict]) -> None:
    """Cores do modelo — tabela única, partilhada por todas as famílias."""
    if not rows:
        return
    model_ids = [str(row["id"]) for row in rows if row.get("id")]
    cores_by_model: dict[str, list[dict]] = {mid: [] for mid in model_ids}
    if model_ids:
        direct = (
            get_db()
            .table(PRODUCT_MODEL_COLORS_TABLE)
            .select("id_modelo, numero, nome, imagem, visibilidade")
            .in_("id_modelo", model_ids)
            .execute()
            .data
            or []
        )
        for cor in direct:
            mid = str(cor.get("id_modelo") or "")
            if mid in cores_by_model:
                cores_by_model[mid].append(cor)
    for row in rows:
        mid = str(row.get("id") or "")
        row["modelo_cores"] = _modelo_cores({"modelo_cores": cores_by_model.get(mid, [])})


def _lookup_cor_nome(db, *, id_modelo: str | None, numero_cor: int) -> str:
    cor_nome = f"Cor {numero_cor}"
    if not id_modelo:
        return cor_nome
    cr = (
        db.table(PRODUCT_MODEL_COLORS_TABLE)
        .select("nome, numero")
        .eq("id_modelo", str(id_modelo))
        .eq("numero", numero_cor)
        .limit(1)
        .execute()
    )
    if cr.data:
        return cr.data[0].get("nome") or cor_nome
    return cor_nome


def _require_public_category(id_categoria: str) -> bool:
    """Categoria tem de existir e estar visível na loja (anti-IDOR por UUID oculto)."""
    try:
        res = get_db().table("categories").select("id,visibilidade").eq("id", id_categoria).limit(1).execute()
    except Exception:
        return False
    rows = res.data or []
    if not rows:
        return False
    return is_visible(rows[0])


def _flatten_attrs(row: dict) -> dict:
    """Expõe os atributos específicos da categoria também no nível de topo do
    dict — mantém a resposta da API da loja igual à de antes do esquema
    unificado (ex.: `product.dimensoes`, `model.tipo_oculo`), para o
    frontend-web não ter de saber que esses campos agora vivem em
    `attributes` (jsonb, só relevante à escrita/validação no backoffice)."""
    attrs = row.get("attributes")
    if isinstance(attrs, dict) and attrs:
        return {**attrs, **row}
    return row


def _finalize_model_products(row: dict, pt: str, mode: str) -> bool:
    """Ordena variantes visíveis; devolve False se não houver produto/cor publicáveis."""
    # Sem cores o detalhe não tem imagem — não listar o modelo na loja.
    if not _modelo_cores(row):
        return False

    raw = row.get(pt)
    products = _visible_products(raw if isinstance(raw, list) else [raw] if raw else [])
    products = [_flatten_attrs(p) for p in products]

    if mode == "unico":
        if not products:
            return False
        row[pt] = products[0] if len(products) == 1 else products
        return True

    if mode == "assento":
        if not products:
            return False
        products.sort(key=lambda p: str(p.get("altura") or ""))
        row[pt] = products
        return True

    if not products:
        return False
    products.sort(key=lambda p: str(p.get("dimensoes") or p.get("segmento") or ""))
    row[pt] = products
    return True


# Campos de atributo que podem ser filtrados ao nível da variante (não do modelo).
_PRODUCT_FILTER_ATTRS = frozenset({"dimensoes", "altura", "segmento"})


_SAFE_ATTR = re.compile(r"[a-z][a-z0-9_]{0,39}")


def _split_filters(filters: dict[str, str] | None) -> tuple[dict[str, str], dict[str, str]]:
    model_filters: dict[str, str] = {}
    product_filters: dict[str, str] = {}
    for field, value in (filters or {}).items():
        if not field or field.startswith("_") or value is None or not str(value).strip():
            continue
        # O nome vem da query string e entra no caminho PostgREST `attributes->>{field}`:
        # só nomes simples de atributo (sem `->`, vírgulas, parênteses, operadores).
        if not _SAFE_ATTR.fullmatch(field):
            continue
        text = str(value)
        if field == "ean":
            continue  # EAN já é um campo próprio, não um atributo
        if field in _PRODUCT_FILTER_ATTRS:
            product_filters[field] = text
        else:
            model_filters[field] = text
    return model_filters, product_filters


def _matches_product_filters(row: dict, pt: str, product_filters: dict[str, str]) -> bool:
    if not product_filters:
        return True
    raw = row.get(pt)
    products = raw if isinstance(raw, list) else [raw] if raw else []
    for product in products:
        if not isinstance(product, dict):
            continue
        attrs = product.get("attributes") or {}
        if all(str(attrs.get(field) or "") == value for field, value in product_filters.items()):
            return True
    return False


def catalogue_models_for_tipo(
    tipo: str,
    id_categoria: str,
    *,
    filters: dict[str, str] | None = None,
    filter_field: str | None = None,
    filter_value: str | None = None,
    limit: int = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
) -> list[dict]:
    if not is_valid_tipo(tipo):
        return []
    if not _require_public_category(id_categoria):
        return []

    cfg = CATALOG_TYPES[tipo]
    mode = cfg.get("storefront_mode") or "variantes"
    pt = PRODUCT_VARIANTS_TABLE

    active_filters = dict(filters or {})
    if filter_field and filter_value:
        active_filters[filter_field] = filter_value

    model_filters, product_filters = _split_filters(active_filters)
    limit = min(max(int(limit or DEFAULT_PAGE_LIMIT), 1), MAX_PAGE_LIMIT)
    offset = max(int(offset or 0), 0)

    query = (
        get_db()
        .table(PRODUCT_MODELS_TABLE)
        .select(f"*, categories({_category_select()}), {pt}({_product_select_fields()})")
        .eq("id_categoria", id_categoria)
        .eq("tipo_catalogo", tipo)
        .eq("visibilidade", True)
    )

    for field, value in model_filters.items():
        query = query.eq(f"attributes->>{field}", value)

    # Pede 1 a mais do que o limite para saber se há próxima página sem outro round-trip.
    rows = (
        query.order("nome").range(offset, offset + limit).execute().data or []
    )
    has_more = len(rows) > limit
    rows = rows[:limit]
    _attach_modelo_cores(rows)
    out: list[dict] = []

    for row in rows:
        row = attach_storefront_fields(dict(row), tipo, cfg)
        row["modelo_cores"] = _modelo_cores(row)
        if not _finalize_model_products(row, pt, mode):
            continue
        if not _matches_product_filters(row, pt, product_filters):
            continue

        row = _flatten_attrs(row)
        row["_tipo_catalogo"] = tipo
        row["_storefront"] = storefront_context_for_tipo(tipo, cfg)
        row["_storefront_mode"] = mode
        out.append(row)

    if out:
        out[-1]["_has_more"] = has_more
    return out


def catalogue_models_aggregated(
    virtual_tipo: str,
    id_categoria: str,
    *,
    filters: dict[str, str] | None = None,
    limit: int = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
) -> list[dict]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from models.schemas import aggregated_tipos_for_tipo

    if not _require_public_category(id_categoria):
        return []

    tipos = aggregated_tipos_for_tipo(virtual_tipo) or []
    family = (filters or {}).get("_tipo_catalogo")
    db_filters = {k: v for k, v in (filters or {}).items() if not k.startswith("_")}
    out: list[dict] = []

    # limit/offset aplicam-se à lista JÁ fundida, não a cada família: aplicá-los
    # por família devolvia até N×limit linhas numa página, e o offset saltava
    # registos em cada família em vez de na lista ordenada, pelo que as páginas
    # seguintes saltavam e repetiam modelos.
    page_limit = min(max(int(limit or DEFAULT_PAGE_LIMIT), 1), MAX_PAGE_LIMIT)
    page_offset = max(int(offset or 0), 0)
    per_family_limit = min(page_offset + page_limit, MAX_PAGE_LIMIT)

    def _fetch(physical: str) -> list[dict]:
        if family and physical != family:
            return []
        rows = catalogue_models_for_tipo(
            physical, id_categoria, filters=db_filters, limit=per_family_limit, offset=0
        )
        batch: list[dict] = []
        for row in rows:
            row["_tipo_catalogo"] = physical
            row["_category_tipo"] = virtual_tipo
            row["_familia_label"] = CATALOG_TYPES[physical]["label"]
            batch.append(row)
        return batch

    with ThreadPoolExecutor(max_workers=min(5, max(len(tipos), 1))) as pool:
        futures = [pool.submit(_fetch, physical) for physical in tipos]
        for fut in as_completed(futures):
            out.extend(fut.result())

    out.sort(key=lambda r: str(r.get("nome") or ""))
    return out[page_offset : page_offset + page_limit]


def model_detail_for_tipo_query(tipo: str, id_modelo: str) -> dict | None:
    batch = models_detail_map_for_tipo(tipo, [id_modelo])
    return batch.get(str(id_modelo))


def _normalize_model_detail_row(data: dict, *, tipo: str, cfg: dict, mode: str) -> dict | None:
    pt = PRODUCT_VARIANTS_TABLE
    if not data or not is_visible(data):
        return None
    parent = data.get("categories") if isinstance(data.get("categories"), dict) else None
    if parent is not None and not is_visible(parent):
        return None
    if parent is None and data.get("id_categoria") and not _require_public_category(str(data["id_categoria"])):
        return None
    if isinstance(data.get("categories"), dict):
        cat = data["categories"]
        data["categories"] = {k: cat.get(k) for k in ("id", "nome", "carrinho_step", "carrinho_min", "slug", "tipo_catalogo")}
    data = attach_storefront_fields(dict(data), tipo, cfg)
    data["modelo_cores"] = _modelo_cores(data)
    if not _finalize_model_products(data, pt, mode):
        return None
    data = _flatten_attrs(data)
    ctx = storefront_context_for_tipo(tipo, cfg)
    data["_tipo_catalogo"] = tipo
    data["_storefront"] = ctx
    data["_storefront_mode"] = mode
    return data


def models_detail_map_for_tipo(tipo: str, model_ids: list[str]) -> dict[str, dict]:
    """Batch fetch — evita N+1 na pesquisa."""
    if not is_valid_tipo(tipo) or not model_ids:
        return {}
    cfg = CATALOG_TYPES[tipo]
    mode = cfg.get("storefront_mode") or "variantes"
    pt = PRODUCT_VARIANTS_TABLE
    ids = [str(i) for i in model_ids if i]
    if not ids:
        return {}
    res = (
        get_db()
        .table(PRODUCT_MODELS_TABLE)
        .select(f"*, categories(*), {pt}(*)")
        .eq("tipo_catalogo", tipo)
        .in_("id", ids)
        .execute()
    )
    rows = res.data or []
    _attach_modelo_cores(rows)
    out: dict[str, dict] = {}
    for row in rows:
        normalized = _normalize_model_detail_row(row, tipo=tipo, cfg=cfg, mode=mode)
        if normalized and row.get("id"):
            out[str(row["id"])] = normalized
    return out


def _resolve_public_category_id(category_slug: str) -> str | None:
    db = get_db()
    key = (category_slug or "").strip()
    if not key:
        return None
    query = db.table("categories").select("id,visibilidade,slug").eq("visibilidade", True)
    if len(key) == 36 and key.count("-") == 4:
        query = query.eq("id", key)
    else:
        query = query.eq("slug", key)
    row = query.limit(1).execute().data
    if not row:
        return None
    return str(row[0]["id"])


def _find_model_id_by_slug(category_id: str, tipo: str, model_key: str) -> str | None:
    query = (
        get_db()
        .table(PRODUCT_MODELS_TABLE)
        .select("id")
        .eq("id_categoria", category_id)
        .eq("tipo_catalogo", tipo)
        .eq("visibilidade", True)
    )
    if len(model_key) == 36 and model_key.count("-") == 4:
        query = query.eq("id", model_key)
    else:
        query = query.eq("slug", model_key)
    row = (query.limit(1).execute().data or [None])[0]
    if not row and not (len(model_key) == 36 and model_key.count("-") == 4):
        row = (
            get_db()
            .table(PRODUCT_MODELS_TABLE)
            .select("id")
            .eq("id_categoria", category_id)
            .eq("tipo_catalogo", tipo)
            .eq("visibilidade", True)
            .ilike("nome", model_key)
            .limit(1)
            .execute()
            .data
            or [None]
        )[0]
    return str(row["id"]) if row else None


def model_detail_for_slugs_query(tipo: str, category_slug: str, model_slug: str) -> dict | None:
    from models.schemas import aggregated_tipos_for_tipo

    model_key = (model_slug or "").strip()
    if not model_key:
        return None
    category_id = _resolve_public_category_id(category_slug)
    if not category_id:
        return None

    aggregated = aggregated_tipos_for_tipo(tipo)
    if aggregated:
        for physical in aggregated:
            model_id = _find_model_id_by_slug(category_id, physical, model_key)
            if model_id:
                data = model_detail_for_tipo_query(physical, model_id)
                if data:
                    data["_tipo_catalogo"] = physical
                    data["_category_tipo"] = tipo
                    data["_familia_label"] = CATALOG_TYPES[physical]["label"]
                    return data
        return None

    if not is_valid_tipo(tipo):
        return None
    model_id = _find_model_id_by_slug(category_id, tipo, model_key)
    if not model_id:
        return None
    return model_detail_for_tipo_query(tipo, model_id)


def _resolve_ean_hit(db, ean: str) -> tuple[str, dict] | None:
    """Lookup via view catalog_ean_lookup; None se view indisponível."""
    try:
        res = (
            db.table("catalog_ean_lookup")
            .select("tipo, id_modelo, product_visivel, model_visivel")
            .eq("ean", ean)
            .limit(1)
            .execute()
        )
        row = (res.data or [None])[0]
    except Exception:
        return None
    if not row or not row.get("product_visivel") or not row.get("model_visivel"):
        return None
    tipo = str(row.get("tipo") or "")
    if not tipo or tipo not in CATALOG_TYPES:
        return None
    item_res = (
        db.table(PRODUCT_VARIANTS_TABLE)
        .select(f"*, {PRODUCT_MODELS_TABLE}(*)")
        .eq("ean", ean)
        .limit(1)
        .execute()
    )
    item = (item_res.data or [None])[0]
    if not item or not is_visible(item):
        return None
    return tipo, item


def _product_line_from_item(db, *, tipo: str, item: dict, ean: str, numero_cor: int, altura: str | None) -> dict | None:
    mode = (CATALOG_TYPES.get(tipo) or {}).get("storefront_mode") or "variantes"
    modelo = item.get(PRODUCT_MODELS_TABLE) or {}
    if isinstance(modelo, list) and modelo:
        modelo = modelo[0]
    if not isinstance(modelo, dict):
        modelo = {}
    if modelo and not is_visible(modelo):
        return None
    id_modelo = item.get("id_modelo")
    cor_nome = _lookup_cor_nome(db, id_modelo=str(id_modelo) if id_modelo else None, numero_cor=numero_cor)
    item_attrs = item.get("attributes") or {}
    dim = altura or item_attrs.get("dimensoes") or ""
    if mode == "assento" and altura:
        dim = altura
    return {
        "ean": ean,
        "numero_cor": numero_cor,
        "altura": altura or "",
        "modelo": modelo.get("nome") or "",
        "dimensoes": dim,
        "cor_nome": cor_nome,
        "tipo_produto": tipo,
    }


def _find_product_by_ean(db, ean: str) -> tuple[str, dict] | None:
    hit = _resolve_ean_hit(db, ean)
    if hit:
        return hit
    row = (
        db.table(PRODUCT_VARIANTS_TABLE)
        .select(f"*, {PRODUCT_MODELS_TABLE}(*)")
        .eq("ean", ean)
        .limit(1)
        .execute()
        .data
        or [None]
    )[0]
    if not row or not is_visible(row):
        return None
    tipo = row.get("tipo_catalogo")
    return (tipo, row) if tipo else None


def resolve_product_line(ean: str, numero_cor: int, altura: str | None = None) -> dict:
    """Resolve EAN + cor (+ altura) para qualquer tipo registado."""
    lines = resolve_product_lines_batch([{"ean": ean, "numero_cor": numero_cor, "altura": altura or ""}])
    return lines[0] if lines else {
        "ean": ean,
        "numero_cor": numero_cor,
        "modelo": "?",
        "dimensoes": "?",
        "cor_nome": f"Cor {numero_cor}",
    }


def resolve_product_lines_batch(linhas: list[dict]) -> list[dict]:
    """Batch EAN lookup — 1 query para todos os EANs (esquema unificado:
    já não há N+1 por família de catálogo)."""
    if not linhas:
        return []
    db = get_db()
    eans = list({str(l.get("ean") or "").strip() for l in linhas if str(l.get("ean") or "").strip()})
    ean_hits: dict[str, tuple[str, dict]] = {}
    if eans:
        items = (
            db.table(PRODUCT_VARIANTS_TABLE)
            .select(f"*, {PRODUCT_MODELS_TABLE}(*)")
            .in_("ean", eans)
            .execute()
            .data
            or []
        )
        for item in items:
            ean = str(item.get("ean") or "")
            tipo = item.get("tipo_catalogo")
            if not ean or not tipo or not is_visible(item):
                continue
            modelo = item.get(PRODUCT_MODELS_TABLE) or {}
            if isinstance(modelo, list) and modelo:
                modelo = modelo[0]
            if isinstance(modelo, dict) and modelo and not is_visible(modelo):
                continue
            ean_hits[ean] = (tipo, item)

    missing = [e for e in eans if e not in ean_hits]
    for ean in missing:
        found = _find_product_by_ean(db, ean)
        if found:
            ean_hits[ean] = found

    out: list[dict] = []
    for linha in linhas:
        ean = str(linha.get("ean") or "").strip()
        numero_cor = int(linha.get("numero_cor") or 0)
        altura = linha.get("altura")
        found = ean_hits.get(ean)
        if found:
            tipo, item = found
            line = _product_line_from_item(db, tipo=tipo, item=item, ean=ean, numero_cor=numero_cor, altura=altura)
            if line:
                out.append({**linha, **line})
                continue
        out.append({**linha, "ean": ean, "numero_cor": numero_cor, "modelo": "?", "dimensoes": "?", "cor_nome": f"Cor {numero_cor}"})
    return out
