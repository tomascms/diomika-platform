"""Texto de pesquisa do utilizador não pode escapar do filtro `.ilike()` e
injetar condições extra num `.or_()` do PostgREST (admin e loja pública)."""
from __future__ import annotations

from utils.postgrest_filter import or_literal


def test_plain_text_is_wrapped_unchanged():
    assert or_literal("almofada") == '"almofada"'


def test_comma_cannot_close_the_condition_early():
    # Sem escape, isto seria interpretado como duas condições do .or_():
    # ean.ilike.%x% , visibilidade.eq.true  — a 2ª sem relação com a pesquisa.
    hostile = "%x%,visibilidade.eq.true"
    escaped = or_literal(hostile)
    assert escaped == '"%x%,visibilidade.eq.true"'
    assert escaped.count('"') == 2  # a vírgula fica presa dentro de UM valor


def test_double_quote_and_backslash_are_escaped():
    assert or_literal('a"b') == '"a\\"b"'
    assert or_literal("a\\b") == '"a\\\\b"'


def test_admin_list_records_search_uses_escaped_pattern():
    import routes.admin_crud as admin_crud

    # mesma lógica que list_records() usa para construir o padrão de pesquisa
    needle = 'x",visibilidade.eq.true'
    pattern = admin_crud.or_literal(f"%{needle}%")
    assert pattern.startswith('"%x\\",visibilidade.eq.true%"')
