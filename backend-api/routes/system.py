from fastapi import APIRouter, HTTPException, Depends, Request
import logging

from core.audit import audit_request
from core.auth import (
    CRUD_INFRA_BLOCKED,
    assert_table_action,
    filter_sidebar_for_role,
    require_admin,
    require_catalog_role,
    require_ops,
    require_pedidos,
    role_can_access_table,
)
from core.config import get_settings
from core.database import get_db
from core.local_only import admin_must_be_local
from models.catalog_registry import catalog_metadata
from models.catalog_views import CATALOG_VIEWS
from models.schemas import TABLE_MAP, sidebar_tables
from core.admin_form_schema import build_form_schema

logger = logging.getLogger("diomika-api")

router = APIRouter(
    prefix="/system",
    tags=["System"],
    dependencies=[Depends(admin_must_be_local)],
)


@router.get("/workspace")
def workspace_config(request: Request, role=Depends(require_admin)):
    """Config leve do backoffice — sidebar + meta de tabelas (sem campos de formulário).

    Schemas de formulário vêm de GET /system/schema/form/{table} sob pedido.
    """
    sidebar = {}
    for key, cfg in sidebar_tables().items():
        sidebar[key] = {
            "label": cfg.get("label", key),
            "icon": cfg.get("icon", "folder"),
            "ui_mode": cfg.get("ui_mode"),
            "ui_catalog_merged_list": cfg.get("ui_catalog_merged_list") or key in CATALOG_VIEWS,
        }
    sidebar = filter_sidebar_for_role(sidebar, str(role))
    tables = {}
    for name, cfg in TABLE_MAP.items():
        if name in CRUD_INFRA_BLOCKED or cfg.get("ui_hidden_infra"):
            continue
        if not role_can_access_table(str(role), name):
            continue
        schema = cfg.get("schema")
        if not schema:
            continue
        tables[name] = {
            "label": cfg.get("label", name),
            "ui_embed_colors": bool(cfg.get("ui_embed_colors")),
            "ui_list_formatter": cfg.get("ui_list_formatter"),
            "list_label_fields": cfg.get("list_label_fields"),
        }
    for view_key in CATALOG_VIEWS:
        if not role_can_access_table(str(role), view_key):
            continue
        tables[view_key] = {
            "label": CATALOG_VIEWS[view_key]["label"],
            "ui_catalog_merged_list": True,
            "list_label_fields": ["nome"],
        }

    return {
        "sidebar": sidebar,
        "tables": tables,
        "catalog": catalog_metadata(),
        "actor": getattr(request.state, "api_actor", None),
        "role": role,
    }


@router.get("/schema/form/{table_name}")
def form_schema(request: Request, table_name: str, role=Depends(require_admin)):
    # build primeiro: dá 404 para tabela não registada, antes do 403 de papel,
    # que era a ordem de erros desta rota antes de a construção ser extraída.
    schema = build_form_schema(table_name)
    assert_table_action(table_name, "read", role)
    return schema


@router.get("/categories/tipos", dependencies=[Depends(require_catalog_role)])
def categories_available_tipos():
    """Famílias de produto disponíveis para uma categoria nova — CRUD real:
    uma categoria pode ser criada com qualquer nome/imagem, para qualquer
    família (incluindo várias categorias para a mesma família, ex. "Almofadas
    de Natal" e "Almofadas" podem coexistir). A criação em si usa o CRUD
    genérico (POST /admin/crud/categories) — este endpoint só alimenta o
    dropdown de família no formulário."""
    from models.catalog_registry import CATALOG_TYPES

    return {"tipos": [{"tipo": tipo, "label": cfg["label"]} for tipo, cfg in sorted(CATALOG_TYPES.items())]}


@router.get("/order-picker/{category_id}", dependencies=[Depends(require_pedidos)])
def order_picker_for_category(category_id: str):
    """Dados para criar linhas de encomenda — genérico por tipo de catálogo."""
    from models.catalog_registry import CATALOG_TYPES, storefront_mode_for_tipo, tipo_label
    from models.schemas import PRODUCT_MODEL_COLORS_TABLE, PRODUCT_MODELS_TABLE, PRODUCT_VARIANTS_TABLE, aggregated_tipos_for_tipo

    cat_res = get_db().table("categories").select("*").eq("id", category_id).execute()
    if not cat_res.data:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    cat = cat_res.data[0]
    tipo = cat.get("tipo_catalogo")
    aggregated = aggregated_tipos_for_tipo(tipo) or []
    if not tipo or (tipo not in CATALOG_TYPES and not aggregated):
        raise HTTPException(status_code=400, detail="Categoria sem tipo de catálogo válido")

    step = cat.get("carrinho_step") or 6
    min_q = cat.get("carrinho_min") or step
    db = get_db()

    def _assento_lines(physical: str) -> list[dict]:
        models = (
            db.table(PRODUCT_MODELS_TABLE)
            .select("id, nome, attributes")
            .eq("id_categoria", category_id)
            .eq("tipo_catalogo", physical)
            .eq("visibilidade", True)
            .execute()
            .data
            or []
        )
        model_by_id = {str(m["id"]): m for m in models}
        model_ids = list(model_by_id.keys())
        if not model_ids:
            return []

        products = (
            db.table(PRODUCT_VARIANTS_TABLE)
            .select("ean, attributes, id_modelo")
            .in_("id_modelo", model_ids)
            .eq("visibilidade", True)
            .execute()
            .data
            or []
        )
        products_by_model: dict[str, list] = {}
        for p in products:
            if str(p.get("ean") or "").strip():
                mid = str(p["id_modelo"])
                products_by_model.setdefault(mid, []).append(p)
        for lst in products_by_model.values():
            lst.sort(key=lambda p: str((p.get("attributes") or {}).get("altura") or ""))

        cores_res = (
            db.table(PRODUCT_MODEL_COLORS_TABLE)
            .select("id_modelo, numero, nome")
            .in_("id_modelo", model_ids)
            .eq("visibilidade", True)
            .execute()
            .data
            or []
        )
        cores_by_model: dict[str, list] = {}
        for c in cores_res:
            mid = str(c["id_modelo"])
            cores_by_model.setdefault(mid, []).append({"numero": c["numero"], "nome": c.get("nome") or ""})

        lines = []
        for m in models:
            mid = str(m["id"])
            prods = products_by_model.get(mid, [])
            lines.append({
                "modelo_id": mid,
                "modelo_nome": m["nome"],
                "ean": (prods[0].get("ean") if prods else None),
                "products": [
                    {"ean": p["ean"], "altura": (p.get("attributes") or {}).get("altura")}
                    for p in prods
                ],
                "alturas": [
                    (p.get("attributes") or {}).get("altura") for p in prods
                    if (p.get("attributes") or {}).get("altura")
                ] or ((m.get("attributes") or {}).get("alturas") or []),
                "cores": cores_by_model.get(mid, []),
            })
        return lines

    def _variant_products(physical: str) -> list[dict]:
        models = (
            db.table(PRODUCT_MODELS_TABLE)
            .select("id, nome")
            .eq("id_categoria", category_id)
            .eq("tipo_catalogo", physical)
            .eq("visibilidade", True)
            .execute()
            .data
            or []
        )
        model_by_id = {str(m["id"]): m for m in models}
        model_ids = list(model_by_id.keys())
        if not model_ids:
            return []
        products = (
            db.table(PRODUCT_VARIANTS_TABLE)
            .select("ean, attributes, id_modelo")
            .in_("id_modelo", model_ids)
            .eq("visibilidade", True)
            .execute()
            .data
            or []
        )
        cores_res = (
            db.table(PRODUCT_MODEL_COLORS_TABLE)
            .select("id_modelo, numero, nome")
            .in_("id_modelo", model_ids)
            .eq("visibilidade", True)
            .execute()
        )
        cores_map: dict[str, list] = {}
        for c in cores_res.data or []:
            mid = str(c["id_modelo"])
            cores_map.setdefault(mid, []).append({"numero": c["numero"], "nome": c.get("nome") or ""})
        family = tipo_label(physical)
        enriched = []
        for p in products:
            if not str(p.get("ean") or "").strip():
                continue
            mid = str(p.get("id_modelo") or "")
            modelo = model_by_id.get(mid) or {}
            attrs = p.get("attributes") or {}
            dim = attrs.get("dimensoes") or attrs.get("segmento") or ""
            enriched.append(
                {
                    "ean": p["ean"],
                    "dimensoes": dim,
                    "modelo_nome": modelo.get("nome") or "",
                    "familia": family,
                    "cores": cores_map.get(mid, []),
                }
            )
        return enriched

    if tipo == "assento" or (not aggregated and storefront_mode_for_tipo(tipo) == "assento"):
        return {
            "mode": "assento",
            "tipo": tipo,
            "carrinho_step": step,
            "carrinho_min": min_q,
            "models": _assento_lines("assento"),
        }

    physical_tipos = aggregated or [tipo]
    products: list[dict] = []
    for physical in physical_tipos:
        if physical not in CATALOG_TYPES:
            continue
        if storefront_mode_for_tipo(physical) == "assento":
            continue
        products.extend(_variant_products(physical))

    return {
        "mode": "variantes",
        "tipo": tipo,
        "carrinho_step": step,
        "carrinho_min": min_q,
        "products": products,
    }
