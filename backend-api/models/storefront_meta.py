"""Metadados de vitrine — esquema unificado: derivados do registo de atributos
por categoria (models/catalog_attributes.py), não de introspecção Pydantic.

Antes do refactor, cada família tinha a sua própria classe Pydantic e esta
função lia `model_schema.model_fields` para descobrir "qual campo é o
seletor de tamanho" etc. Agora todas as famílias partilham a mesma classe
(ProductModel/ProductVariant) — os campos que variam por família vivem em
`attributes`, descritos em CATEGORY_ATTRIBUTE_SCHEMAS.
"""
from __future__ import annotations

import json
from typing import Any

from models.catalog_attributes import CATEGORY_ATTRIBUTE_SCHEMAS


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return sorted(str(v).strip() for v in value if v and str(v).strip())
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return sorted(str(v).strip() for v in parsed if v and str(v).strip())
        except json.JSONDecodeError:
            pass
        return [value.strip()] if value.strip() else []
    return []


def _model_attrs(tipo: str) -> dict:
    return (CATEGORY_ATTRIBUTE_SCHEMAS.get(tipo) or {}).get("model_attributes") or {}


def _variant_attrs(tipo: str) -> dict:
    return (CATEGORY_ATTRIBUTE_SCHEMAS.get(tipo) or {}).get("variant_attributes") or {}


def storefront_picker_for_type(cfg: dict) -> dict | None:
    """Configuração do selector na página de produto (tamanho, altura, etc.)."""
    mode = cfg.get("storefront_mode") or "variantes"
    if mode == "unico":
        return None
    if cfg.get("storefront_picker"):
        return dict(cfg["storefront_picker"])

    tipo = cfg.get("_tipo") or ""
    if mode == "assento":
        for name, desc in _model_attrs(tipo).items():
            if desc["type"] == "string_list":
                return {"source": "model", "field": name, "label": desc.get("label") or "Variante", "format": "plain"}
        return {"source": "model", "field": "alturas", "label": "Variante", "format": "plain"}

    for name, desc in _variant_attrs(tipo).items():
        if desc["type"] == "dimension_single":
            return {
                "source": "products",
                "field": name,
                "label": desc.get("label") or "Tamanho",
                "format": "dimensions",
                "suffix": " cm",
            }
    for name, desc in _variant_attrs(tipo).items():
        if not desc.get("hidden"):
            return {"source": "products", "field": name, "label": desc.get("label") or "Tamanho", "format": "plain"}
    return None


def storefront_specs_for_model(tipo: str, picker: dict | None = None, badge: dict | None = None) -> list[dict]:
    """Atributos do modelo a mostrar na ficha de produto da loja."""
    picker_field = picker.get("field") if picker and picker.get("source") == "model" else None
    badge_field = badge.get("field") if badge else None
    specs: list[dict] = []
    for name, desc in _model_attrs(tipo).items():
        if desc.get("hidden") or name in (picker_field, badge_field):
            continue
        if desc["type"] == "string_list":
            continue  # já representado pelo picker, quando aplicável
        specs.append(
            {
                "field": name,
                "label": desc.get("label") or name.replace("_", " ").title(),
                "widget": desc["type"],
                "enum_labels": dict(desc.get("labels") or {}),
            }
        )
    return specs


def storefront_badge_for_model(tipo: str) -> dict | None:
    """Primeiro atributo enum do modelo — badge na grelha de produtos."""
    for name, desc in _model_attrs(tipo).items():
        if desc["type"] == "enum" and not desc.get("hidden"):
            return {"field": name, "labels": dict(desc.get("labels") or {})}
    return None


def storefront_context_for_tipo(tipo: str, cfg: dict) -> dict:
    cfg = {**cfg, "_tipo": tipo}
    picker = storefront_picker_for_type(cfg)
    badge = storefront_badge_for_model(tipo)
    return {
        "mode": cfg.get("storefront_mode") or "variantes",
        "product_table": cfg["product_table"],
        "picker": picker,
        "specs": storefront_specs_for_model(tipo, picker, badge),
        "badge": badge,
    }


def attach_storefront_fields(data: dict, tipo: str, cfg: dict) -> dict:
    """Normaliza campos usados pelo picker (ex.: listas JSON de alturas)."""
    picker = storefront_picker_for_type({**cfg, "_tipo": tipo})
    if picker and picker.get("source") == "model":
        field = picker.get("field")
        attrs = data.get("attributes") or {}
        if field and field in attrs:
            attrs[field] = _normalize_string_list(attrs[field])
            data["attributes"] = attrs
    return data
