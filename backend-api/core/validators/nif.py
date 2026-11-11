"""NIF português: 9 dígitos, o último é de controlo (módulo 11).

Espelha frontend-web/src/lib/nif.js: mudar nos dois (os testes usam os mesmos valores).
Um número que não tenha 9 dígitos (depois de tirar espaços, pontos, hífenes e «PT») é
estrangeiro e não se verifica: o campo é facultativo e a loja vende também fora de Portugal.
"""
from __future__ import annotations

import re

_SEPARATORS = re.compile(r"[\s.\-]")
_PT_PREFIX = re.compile(r"^PT", re.IGNORECASE)


def is_valid_nif(nif: str) -> bool:
    """NIF português válido: 9 dígitos (o primeiro nunca é 0) e dígito de controlo certo."""
    if not re.fullmatch(r"[1-9]\d{8}", nif or ""):
        return False
    total = sum(int(digit) * weight for digit, weight in zip(nif, range(9, 1, -1)))
    check = 11 - total % 11
    return int(nif[8]) == (0 if check >= 10 else check)


def clean_nif(raw: str) -> str:
    """O valor a guardar. Um número com 9 dígitos (com ou sem «PT» e separadores) tem de ter o
    dígito de controlo certo e guarda-se só com os 9 dígitos; senão levanta ValueError. Qualquer
    outro formato é estrangeiro e guarda-se como foi escrito."""
    text = raw.strip()
    digits = _PT_PREFIX.sub("", _SEPARATORS.sub("", text))
    if not re.fullmatch(r"\d{9}", digits):
        return text
    if not is_valid_nif(digits):
        raise ValueError("NIF inválido")
    return digits
