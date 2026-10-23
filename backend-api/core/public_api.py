"""Campos expostos em endpoints públicos da loja."""
from __future__ import annotations

PUBLIC_CATEGORY_FIELDS = (
    "id,nome,slug,imagem,tipo_catalogo,carrinho_step,carrinho_min"
)


def public_category(row: dict) -> dict:
    return {k: row[k] for k in PUBLIC_CATEGORY_FIELDS.split(",") if k in row}
