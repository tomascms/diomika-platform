"""Conteúdo em falta no catálogo (RP-11): o que falta preencher em cada modelo, para o cliente saber por onde começar.

Uma só consulta por tabela (modelos, cores, EAN). «Imagem de demonstração» é a imagem que aparece em mais de um
modelo (o logótipo usado como foto, RP-01): não precisa de saber o ficheiro.
"""
from __future__ import annotations

import re
from collections import defaultdict

from core.database import get_db
from models.catalog_attributes import CATEGORY_ATTRIBUTE_SCHEMAS
from models.catalog_registry import model_table_for_tipo

NO_DESCRIPTION = re.compile(r"^\s*(sem descri[cç][aã]o)?\s*$", re.I)


def _has_composition(tipo: str) -> bool:
    return "composicao" in ((CATEGORY_ATTRIBUTE_SCHEMAS.get(tipo) or {}).get("model_attributes") or {})


def find_missing(models: list[dict], colours: list[dict], variants: list[dict]) -> list[dict]:
    """Um item por modelo com pelo menos uma falta: {id, nome, tabela, visivel, faltas: [texto, …]}."""
    by_model_colours: dict[str, list[dict]] = defaultdict(list)
    for colour in colours:
        by_model_colours[str(colour.get("id_modelo"))].append(colour)
    with_ean = {str(v.get("id_modelo")) for v in variants if str(v.get("ean") or "").strip()}

    image_models: dict[str, set[str]] = defaultdict(set)
    for colour in colours:
        image = str(colour.get("imagem") or "").strip()
        if image:
            image_models[image].add(str(colour.get("id_modelo")))
    shared = {image for image, ids in image_models.items() if len(ids) > 1}

    out = []
    for model in models:
        mid = str(model["id"])
        tipo = str(model.get("tipo_catalogo") or "")
        own = by_model_colours.get(mid, [])
        faltas = []
        if NO_DESCRIPTION.match(str(model.get("descricao") or "")):
            faltas.append("Sem descrição")
        attrs = model.get("attributes") or {}
        if _has_composition(tipo) and not attrs.get("composicao"):
            faltas.append("Sem composição")
        if mid not in with_ean:
            faltas.append("Sem EAN")
        images = [str(c.get("imagem") or "").strip() for c in own]
        if not any(images):
            faltas.append("Sem imagem")
        elif all((not image) or image in shared for image in images):
            faltas.append("Só imagem de demonstração")
        if own and all(str(c.get("nome") or "").strip().lower() in ("", "sortido") for c in own):
            faltas.append("Só a cor «Sortido»")
        if faltas:
            out.append(
                {
                    "id": mid,
                    "nome": model.get("nome") or "",
                    "tabela": model_table_for_tipo(tipo),
                    "visivel": bool(model.get("visibilidade")),
                    "faltas": faltas,
                }
            )
    out.sort(key=lambda item: (-len(item["faltas"]), item["nome"].lower()))
    return out


def missing_content() -> list[dict]:
    db = get_db()
    models = db.table("product_models").select("id,nome,tipo_catalogo,descricao,attributes,visibilidade").limit(1000).execute().data or []
    colours = db.table("product_model_colors").select("id_modelo,nome,imagem").limit(5000).execute().data or []
    variants = db.table("product_variants").select("id_modelo,ean").limit(10000).execute().data or []
    return find_missing(models, colours, variants)
