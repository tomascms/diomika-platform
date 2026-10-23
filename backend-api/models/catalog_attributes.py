"""
Registo de atributos por categoria de catálogo — FONTE DE VERDADE do "formato" de
cada família de produto (almofadas, assentos, toalhas de mesa, ...).

Substitui as antigas 13 famílias de classes Pydantic + 13 trios de tabelas SQL.
Agora há só 3 tabelas físicas (product_models, product_model_colors,
product_variants) e os campos que variam por categoria (tipo, composição,
dimensões, altura, ...) vivem na coluna `attributes jsonb`, validados aqui.

Para adicionar uma categoria nova (ex.: mantas):
  1. Acrescenta uma entrada a CATEGORY_ATTRIBUTE_SCHEMAS (só dados — nenhuma
     classe nova, nenhuma tabela nova, nenhuma migração SQL).
  2. Reinicia a API.
  3. Cria a categoria no backoffice (CRUD real — ver routes/categories.py).

Cada atributo é um dict com:
  type      — "enum" | "composition" | "dimension_list" | "dimension_single"
              | "string_list" | "string_single" | "string"
  required  — bool
  label     — rótulo no formulário
  widget    — widget explícito (opcional; inferido do type se omitido)
  options/labels — para "enum"
  hidden    — campo legado, não mostrar no formulário (continua validado se vier)
  lock_on_edit — variantes: não editável depois de criado (chave de negócio)
  placeholder — texto de apoio no formulário
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal

from models.catalog_validators import (
    validate_composicao_pct,
    validate_dimensao_single,
    validate_dimensoes_list,
    validate_string_list,
)

AttrLevel = Literal["model", "variant"]

TIPO_ALMOFADA_LABELS = {"decorativa": "Decorativa", "dormir": "Dormir"}
TIPO_OCULO_LABELS = {"sol": "Óculos de sol", "leitura": "Óculos de leitura"}
SEGMENTO_OCULO_LABELS = {"homem": "Homem", "mulher": "Mulher", "crianca": "Criança"}
TIPO_TOALHA_MESA_LABELS = {"toalha": "Toalha de mesa", "protetor": "Protetor de mesa"}
MATERIAL_TOALHA_LABELS = {"pvc": "PVC", "poliester": "Poliéster"}
SUBTIPO_REGIONAL_LABELS = {
    "avental": "Avental",
    "luva": "Luva",
    "pega": "Pega",
    "pano_cozinha": "Pano de cozinha",
    "toalha": "Toalha de mesa",
    "protetor": "Protetor de mesa",
}

_DIMENSOES_MODEL_FIELD: dict = {
    "type": "dimension_list",
    "required": True,
    "label": "Dimensões (comprimento×largura)",
    "placeholder": "ex: 100x200",
}
_DIMENSOES_MODEL_FIELD_OPTIONAL: dict = {**_DIMENSOES_MODEL_FIELD, "required": False}
_DIMENSOES_VARIANT_FIELD: dict = {
    "type": "dimension_single",
    "required": True,
    "label": "Dimensão",
    "widget": "dimensao_modelo",
    "lock_on_edit": True,
}
_DIMENSOES_VARIANT_FIELD_OPTIONAL: dict = {**_DIMENSOES_VARIANT_FIELD, "required": False}
_COMPOSICAO_FIELD: dict = {
    "type": "composition",
    "required": True,
    "label": "Composição (%) — igual para todas as cores",
}


def _regional_cross_validate(model_attrs: Dict[str, Any]) -> None:
    subtipo = model_attrs.get("subtipo")
    needs_dim = subtipo in ("pano_cozinha", "toalha", "protetor")
    if needs_dim and not model_attrs.get("dimensoes"):
        raise ValueError("Indique dimensões comprimento×largura (ex: 100x200) para este subtipo.")


CATEGORY_ATTRIBUTE_SCHEMAS: Dict[str, dict] = {
    "almofada": {
        "label": "Almofadas",
        "model_discriminator_field": "dimensoes",
        "product_readonly_on_edit": True,
        "apply_barcode_on_save": True,
        "storefront_mode": "variantes",
        "storefront_filters": [
            {"field": "tipo", "label": "Tipo de Almofada", "options": ["decorativa", "dormir"], "labels": TIPO_ALMOFADA_LABELS},
        ],
        "storefront_picker": {"source": "products", "field": "dimensoes", "label": "Dimensão (comprimento×largura)", "format": "dimensions", "suffix": " cm"},
        "model_attributes": {
            "tipo": {"type": "enum", "required": True, "label": "Tipo de Almofada", "options": ["decorativa", "dormir"], "labels": TIPO_ALMOFADA_LABELS},
            "composicao": _COMPOSICAO_FIELD,
            "dimensoes": _DIMENSOES_MODEL_FIELD,
        },
        "variant_attributes": {
            "dimensoes": _DIMENSOES_VARIANT_FIELD,
        },
    },
    "assento": {
        "label": "Assentos",
        "model_discriminator_field": "alturas",
        "product_readonly_on_edit": True,
        "apply_barcode_on_save": True,
        "storefront_mode": "assento",
        "storefront_picker": {"source": "products", "field": "altura", "label": "Altura", "format": "plain"},
        "model_attributes": {
            "material_forro": {"type": "string", "required": True, "label": "Material do forro"},
            "material_enchimento": {"type": "string", "required": True, "label": "Material do enchimento"},
            "alturas": {
                "type": "string_list",
                "required": True,
                "label": "Alturas (mm)",
                "placeholder": "ex: 32mm",
            },
        },
        "variant_attributes": {
            "altura": {
                "type": "string_single",
                "required": True,
                "label": "Altura",
                "widget": "altura_modelo",
                "lock_on_edit": True,
            },
        },
    },
    "guarda_chuva": {
        "label": "Guarda-chuvas",
        "model_discriminator_field": None,
        "product_readonly_on_edit": True,
        "apply_barcode_on_save": True,
        "storefront_mode": "unico",
        "model_attributes": {},
        "variant_attributes": {},
    },
    "oculo": {
        "label": "Óculos",
        "model_discriminator_field": None,
        "product_readonly_on_edit": True,
        "apply_barcode_on_save": True,
        "storefront_mode": "unico",
        "storefront_filters": [
            {"field": "tipo_oculo", "label": "Tipo", "options": ["sol", "leitura"], "labels": TIPO_OCULO_LABELS},
        ],
        "model_attributes": {
            "tipo_oculo": {"type": "enum", "required": True, "label": "Tipo", "options": ["sol", "leitura"], "labels": TIPO_OCULO_LABELS},
        },
        "variant_attributes": {
            "segmento": {
                "type": "enum",
                "required": False,
                "label": "Segmento (legado — oculto no backoffice)",
                "options": ["homem", "mulher", "crianca"],
                "labels": SEGMENTO_OCULO_LABELS,
                "hidden": True,
            },
        },
    },
    "toalha_mesa": {
        "label": "Toalhas de mesa",
        "model_discriminator_field": "dimensoes",
        "product_readonly_on_edit": True,
        "apply_barcode_on_save": True,
        "storefront_mode": "variantes",
        "storefront_filters": [
            {"field": "tipo_produto", "label": "Tipo", "options": ["toalha", "protetor"], "labels": TIPO_TOALHA_MESA_LABELS},
        ],
        "storefront_picker": {"source": "products", "field": "dimensoes", "label": "Dimensão (comprimento×largura)", "format": "dimensions", "suffix": " cm"},
        "model_attributes": {
            "tipo_produto": {"type": "enum", "required": True, "label": "Tipo", "options": ["toalha", "protetor"], "labels": TIPO_TOALHA_MESA_LABELS},
            "material": {
                "type": "enum",
                "required": False,
                "label": "Material",
                "options": ["pvc", "poliester"],
                "labels": MATERIAL_TOALHA_LABELS,
                "hidden": True,
            },
            "composicao": _COMPOSICAO_FIELD,
            "dimensoes": _DIMENSOES_MODEL_FIELD,
        },
        "variant_attributes": {
            "dimensoes": _DIMENSOES_VARIANT_FIELD,
        },
    },
    "avental": {
        "label": "Aventais",
        "model_discriminator_field": None,
        "apply_barcode_on_save": True,
        "storefront_mode": "unico",
        "model_attributes": {"composicao": _COMPOSICAO_FIELD},
        "variant_attributes": {},
    },
    "luva": {
        "label": "Luvas",
        "model_discriminator_field": None,
        "apply_barcode_on_save": True,
        "storefront_mode": "unico",
        "model_attributes": {"composicao": _COMPOSICAO_FIELD},
        "variant_attributes": {},
    },
    "pega": {
        "label": "Pegas",
        "model_discriminator_field": None,
        "apply_barcode_on_save": True,
        "storefront_mode": "unico",
        "model_attributes": {"composicao": _COMPOSICAO_FIELD},
        "variant_attributes": {},
    },
    "pano_cozinha": {
        "label": "Panos de cozinha",
        "model_discriminator_field": "dimensoes",
        "product_readonly_on_edit": True,
        "apply_barcode_on_save": True,
        "storefront_mode": "variantes",
        "storefront_picker": {"source": "products", "field": "dimensoes", "label": "Dimensão (comprimento×largura)", "format": "dimensions", "suffix": " cm"},
        "model_attributes": {
            "composicao": _COMPOSICAO_FIELD,
            "dimensoes": _DIMENSOES_MODEL_FIELD,
        },
        "variant_attributes": {"dimensoes": _DIMENSOES_VARIANT_FIELD},
    },
    "protetor_colchao": {
        "label": "Protetor de colchão",
        "model_discriminator_field": "dimensoes",
        "product_readonly_on_edit": True,
        "apply_barcode_on_save": True,
        "storefront_mode": "variantes",
        "storefront_picker": {"source": "products", "field": "dimensoes", "label": "Dimensão (comprimento×largura)", "format": "dimensions", "suffix": " cm"},
        "model_attributes": {
            "composicao": _COMPOSICAO_FIELD,
            "dimensoes": _DIMENSOES_MODEL_FIELD,
        },
        "variant_attributes": {"dimensoes": _DIMENSOES_VARIANT_FIELD},
    },
    "passadeira": {
        "label": "Passadeira",
        "model_discriminator_field": "dimensoes",
        "product_readonly_on_edit": True,
        "apply_barcode_on_save": True,
        "storefront_mode": "variantes",
        "storefront_picker": {"source": "products", "field": "dimensoes", "label": "Dimensão (comprimento×largura)", "format": "dimensions", "suffix": " cm"},
        "model_attributes": {
            "composicao": _COMPOSICAO_FIELD,
            "dimensoes": _DIMENSOES_MODEL_FIELD,
        },
        "variant_attributes": {"dimensoes": _DIMENSOES_VARIANT_FIELD},
    },
    "regional": {
        "label": "Regional",
        "model_discriminator_field": "dimensoes",
        "product_readonly_on_edit": True,
        "apply_barcode_on_save": True,
        "storefront_mode": "variantes",
        "storefront_filters": [
            {
                "field": "subtipo",
                "label": "Tipo",
                "options": ["avental", "luva", "pega", "pano_cozinha", "toalha", "protetor"],
                "labels": SUBTIPO_REGIONAL_LABELS,
            },
        ],
        "storefront_picker": {"source": "products", "field": "dimensoes", "label": "Dimensão (comprimento×largura)", "format": "dimensions", "suffix": " cm"},
        "model_attributes": {
            "subtipo": {
                "type": "enum",
                "required": True,
                "label": "Tipo",
                "options": ["avental", "luva", "pega", "pano_cozinha", "toalha", "protetor"],
                "labels": SUBTIPO_REGIONAL_LABELS,
            },
            "composicao": _COMPOSICAO_FIELD,
            "dimensoes": _DIMENSOES_MODEL_FIELD_OPTIONAL,
        },
        "variant_attributes": {"dimensoes": _DIMENSOES_VARIANT_FIELD_OPTIONAL},
        "cross_field_validator": _regional_cross_validate,
    },
}

# Categorias "agregadas" (vitrine única sobre várias tipo_catalogo) — material de cozinha.
AGGREGATED_CATEGORY_GROUPS: Dict[str, List[str]] = {
    "material_cozinha": ["avental", "luva", "pega", "pano_cozinha"],
}

# Nomes de tabela "virtuais" por tipo_catalogo — mantidos iguais aos nomes físicos
# de antes do refactor, por compatibilidade com as rotas do backoffice
# (/admin/crud/{table}) e o frontend, que continuam a usar estes nomes como
# identificador de "formulário". Resolvidos para as 3 tabelas físicas reais
# (product_models / product_variants / product_model_colors) + filtro
# `tipo_catalogo` em models/table_map_builder.py e models/catalog_registry.py.
VIRTUAL_TABLE_NAMES: Dict[str, dict] = {
    "almofada": {"model": "modelos_almofadas", "variant": "almofada", "colors": "modelo_almofada_cores"},
    "assento": {"model": "modelos_assentos", "variant": "assento", "colors": "modelo_assento_cores"},
    "guarda_chuva": {"model": "modelos_guarda_chuvas", "variant": "guarda_chuva", "colors": "modelo_guarda_chuva_cores"},
    "oculo": {"model": "modelos_oculos", "variant": "oculo", "colors": "modelo_oculo_cores"},
    "toalha_mesa": {"model": "modelos_toalhas_mesa", "variant": "toalha_mesa", "colors": "modelo_toalha_mesa_cores"},
    "avental": {"model": "modelos_aventais", "variant": "avental", "colors": "modelo_avental_cores"},
    "luva": {"model": "modelos_luvas", "variant": "luva", "colors": "modelo_luva_cores"},
    "pega": {"model": "modelos_pegas", "variant": "pega", "colors": "modelo_pega_cores"},
    "pano_cozinha": {"model": "modelos_panos_cozinha", "variant": "pano_cozinha", "colors": "modelo_pano_cozinha_cores"},
    "protetor_colchao": {"model": "modelos_protetores_colchao", "variant": "protetor_colchao", "colors": "modelo_protetor_colchao_cores"},
    "passadeira": {"model": "modelos_passadeiras", "variant": "passadeira", "colors": "modelo_passadeira_cores"},
    "regional": {"model": "modelos_regionais", "variant": "regional", "colors": "modelo_regional_cores"},
}


def default_table_names(tipo: str) -> dict:
    """Famílias novas não precisam de entrada acima: os nomes derivam do tipo."""
    return {"model": f"modelos_{tipo}", "variant": tipo, "colors": f"modelo_{tipo}_cores"}


for _tipo in CATEGORY_ATTRIBUTE_SCHEMAS:
    VIRTUAL_TABLE_NAMES.setdefault(_tipo, default_table_names(_tipo))


def is_registered_tipo(tipo: str | None) -> bool:
    return bool(tipo and tipo in CATEGORY_ATTRIBUTE_SCHEMAS)


def _widget_for(name: str, desc: dict) -> str:
    if desc.get("widget"):
        return desc["widget"]
    t = desc["type"]
    return {
        "enum": "enum",
        "composition": "composition",
        "dimension_list": "string_list",
        "dimension_single": "dimensao_modelo",
        "string_list": "string_list",
        "string_single": "text",
        "string": "text",
    }.get(t, "text")


def attribute_form_fields(tipo: str, level: AttrLevel) -> List[dict]:
    """Campos no mesmo formato que models.ui_schema.get_form_fields produz
    para campos fixos — para o backoffice conseguir fundir os dois.

    `name` é o nome do atributo "nu" (ex.: "tipo", não "attributes.tipo"):
    o formulário genérico do backoffice submete um objecto plano
    `{[field.name]: valor}}`, e é `catalog_registry.fold_attributes()` que
    reconhece esses nomes nus e os dobra em `attributes: {...}` antes da
    validação Pydantic — um "attributes.tipo" como nome não seria reconhecido
    nem pelo formulário nem pelo fold."""
    cfg = CATEGORY_ATTRIBUTE_SCHEMAS.get(tipo) or {}
    attrs = cfg.get(f"{level}_attributes") or {}
    out = []
    for name, desc in attrs.items():
        if desc.get("hidden"):
            continue
        out.append(
            {
                "name": name,
                "label": desc.get("label") or name.replace("_", " ").title(),
                "widget": _widget_for(name, desc),
                "required": bool(desc.get("required")),
                "readonly": False,
                "relation": None,
                "enum_options": desc.get("options"),
                "enum_labels": desc.get("labels") or {},
                "lock_on_edit": bool(desc.get("lock_on_edit")),
                "placeholder": desc.get("placeholder") or "",
            }
        )
    return out


def _validate_one(name: str, desc: dict, value: Any) -> Any:
    t = desc["type"]
    required = bool(desc.get("required"))
    empty = value is None or value == "" or value == [] or value == {}
    if empty:
        if required:
            raise ValueError(f"{desc.get('label') or name}: campo obrigatório.")
        return desc.get("default", value)

    if t == "enum":
        options = desc.get("options") or []
        if options and value not in options:
            raise ValueError(f"{desc.get('label') or name}: valor «{value}» inválido (opções: {', '.join(options)}).")
        return value
    if t == "composition":
        return validate_composicao_pct(dict(value))
    if t == "dimension_list":
        return validate_dimensoes_list(list(value))
    if t == "dimension_single":
        return validate_dimensao_single(str(value))
    if t == "string_list":
        return validate_string_list(list(value), desc.get("label") or name)
    if t in ("string_single", "string"):
        cleaned = str(value).strip()
        if required and not cleaned:
            raise ValueError(f"{desc.get('label') or name}: campo obrigatório.")
        return cleaned
    return value


def validate_attributes(tipo: str, level: AttrLevel, data: dict | None) -> dict:
    """Valida + limpa o dict `attributes` de um modelo/variante contra o
    registo da categoria. Lança ValueError com mensagem em pt-PT no 1º erro."""
    if not is_registered_tipo(tipo):
        raise ValueError(f"tipo_catalogo «{tipo}» não está registado em CATEGORY_ATTRIBUTE_SCHEMAS.")
    cfg = CATEGORY_ATTRIBUTE_SCHEMAS[tipo]
    schema = cfg.get(f"{level}_attributes") or {}
    data = data or {}
    cleaned: dict = {}
    for name, desc in schema.items():
        cleaned[name] = _validate_one(name, desc, data.get(name))

    if level == "model":
        cross = cfg.get("cross_field_validator")
        if cross:
            cross(cleaned)

    return cleaned
