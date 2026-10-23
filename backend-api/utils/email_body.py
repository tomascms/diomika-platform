"""Extrai apenas o texto novo de emails (sem citacoes de respostas anteriores)."""
from __future__ import annotations

import re

_QUOTE_LINE = re.compile(
    r"(?:^On .+ wrote:?$|^Em .+ escreveu:?$|^.+\bescreveu:?$|^.+\bwrote:?$|"
    r"^>+\s|^>{0,2}$|^-{3,}|^_{3,}|^Nova mensagem no formulario|^From:\s|^De:\s|"
    r"^Enviado de:|^Sent from my|^Reply-To:|^Referencia:\s*\[Ref:|^Assunto:|^Telefone:|^Email do cliente:|^Nome:\s|"
    r"^Mensagem:\s*$|^Responda directamente|^Forwarded message|^Mensagem encaminhada)",
    re.IGNORECASE,
)

_DATE_HEADER = re.compile(
    r"(\d{1,2}\s+de\s+\w+\s+de\s+\d{4}|\d{4}-\d{2}-\d{2}|\w+,\s+\d{1,2}\s+\w+\s+de\s+\d{4})",
    re.IGNORECASE,
)

_NOTIFICATION_MARKERS = (
    "nova mensagem no formulario",
    "referencia: [ref:",
    "responda directamente a este email",
    "email do cliente:",
)


def _is_quote_boundary(line: str, next_line: str | None) -> bool:
    stripped = line.strip()
    nxt = (next_line or "").strip().lower()

    if not stripped:
        return False
    if _QUOTE_LINE.search(stripped):
        return True
    if stripped.lower() in ("escreveu:", "wrote:"):
        return True
    if nxt in ("escreveu:", "wrote:"):
        return True
    if nxt.startswith("escreveu") or nxt.startswith("wrote"):
        return True
    if "@" in stripped and nxt in ("escreveu:", "wrote:"):
        return True
    if _DATE_HEADER.search(stripped) and ("@" in stripped or "<" in stripped):
        if nxt in ("escreveu:", "wrote:") or nxt.startswith("escreveu"):
            return True
    lowered = stripped.lower()
    if any(marker in lowered for marker in _NOTIFICATION_MARKERS):
        return True
    return False


def strip_email_quotes(text: str) -> str:
    if not text:
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    result: list[str] = []

    for i, line in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        if _is_quote_boundary(line, nxt):
            break
        if line.strip().startswith(">"):
            break
        result.append(line.rstrip())

    while result and not result[-1].strip():
        result.pop()

    cleaned = "\n".join(result).strip()

    for marker in _NOTIFICATION_MARKERS:
        idx = cleaned.lower().find(marker)
        if idx > 0:
            cleaned = cleaned[:idx].strip()
            break

    return cleaned
