"""Validadores primitivos partilhados pelo catálogo (schemas.py + catalog_attributes.py).

Isolados aqui (em vez de viverem em schemas.py) para quebrar o ciclo de import:
catalog_attributes.py precisa destes validadores e schemas.py precisa de
catalog_attributes.py (CATEGORY_ATTRIBUTE_SCHEMAS) para construir CATALOG_TYPES.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List


def generate_slug(text: str) -> str:
    normalized = unicodedata.normalize("NFD", str(text or "").lower().strip())
    ascii_text = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return re.sub(r"[-\s]+", "-", re.sub(r"[^\w\s-]", "", ascii_text)).strip("-")


def validate_ean(v: str) -> str:
    digits = [int(d) for d in v]
    check = (10 - (sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits[:-1])) % 10)) % 10
    if digits[-1] != check:
        raise ValueError(f"EAN inválido. Check-digit esperado: {check}")
    return v


def validate_composicao_pct(v: Dict[str, int]) -> Dict[str, int]:
    if not v:
        raise ValueError("Indique composição.")
    if sum(v.values()) != 100:
        raise ValueError(f"Soma da composição deve ser 100% (Atual: {sum(v.values())}%)")
    return v


def validate_string_list(v: List[str], label: str = "valores") -> List[str]:
    cleaned = [str(a).strip() for a in v if a and str(a).strip()]
    if not cleaned:
        raise ValueError(f"Indique pelo menos um(a) {label}.")
    return cleaned


def validate_dimensoes_list(v: List[str]) -> List[str]:
    """Dimensões = comprimento×largura (ex: 100x200), nunca altura de assento."""
    cleaned = validate_string_list(v, "dimensão")
    bad = [d for d in cleaned if not re.fullmatch(r"\d+x\d+", d)]
    if bad:
        raise ValueError(
            f"Dimensões devem ser comprimento×largura (ex: 100x200). Inválido: {', '.join(bad)}"
        )
    return cleaned


def validate_dimensao_single(v: str) -> str:
    if not re.fullmatch(r"\d+x\d+", str(v or "").strip()):
        raise ValueError("Dimensão deve ser comprimento×largura (ex: 100x200).")
    return str(v).strip()
