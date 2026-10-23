"""Normalização segura de input textual (NFC + strip de control chars)."""
from __future__ import annotations

import re
import unicodedata

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalize_text(value: str | None, *, max_len: int | None = None) -> str:
    """NFC + remove control chars. Não altera conteúdo semântico útil."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFC", str(value))
    text = _CTRL.sub("", text)
    text = text.strip()
    if max_len is not None and len(text) > max_len:
        text = text[:max_len]
    return text
