"""Escape de valores para filtros .or_()/.ilike() do PostgREST (Supabase).

Texto de pesquisa vindo do utilizador nunca deve ser colado sem escape num
filtro `.or_("campo.ilike.%valor%,...")` — uma vírgula ou parêntese no valor
consegue fechar a condição e começar outra (ex.: pesquisar por
`x,visibilidade.eq.true` acrescentava um filtro extra à query)."""
from __future__ import annotations


def or_literal(value: str) -> str:
    """Embrulha `value` em aspas duplas (com `\\` e `"` escapados, conforme a
    sintaxe de filtros do PostgREST) — dentro das aspas, vírgulas e
    parênteses deixam de ter significado especial."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
