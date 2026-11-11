"""Origem de um pedido (RP-10): de onde veio quem pediu, sem dados pessoais e sem cookies.

A loja guarda estes valores no `sessionStorage` (funcional, declarado na política) e envia-os no formulário.
Aqui só passam as chaves conhecidas, como texto curto: um formulário público não escolhe o que fica na BD.
"""
from __future__ import annotations

from typing import Any

# entrada: caminho da página de entrada (sem query); referrer: só o domínio; produto: último modelo visto.
_KEYS = ("entrada", "referrer", "utm_source", "utm_medium", "utm_campaign", "produto")
_MAX = 120


def clean_origem(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    out: dict[str, str] = {}
    for key in _KEYS:
        raw = value.get(key)
        if isinstance(raw, str):
            text = " ".join(raw.split())[:_MAX]
            if key == "entrada":
                text = text.split("?")[0].split("#")[0]  # nunca a query: pode trazer um email ou um token
            if text:
                out[key] = text
    return out or None
