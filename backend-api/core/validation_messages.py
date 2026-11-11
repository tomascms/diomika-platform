"""Mensagens de validação em português (FE-09, A11Y-07, API-09).

O FastAPI responde 422 com as mensagens do Pydantic, em inglês («String should have at least 2 characters»,
«value is not a valid email address: …»), e repete o que o visitante escreveu (`input`). Aqui cada erro passa a
uma frase em português que se lê junto do campo, e só leva `type`, `loc` e `msg`: o formato de sempre (`detail` é
uma lista), por isso a loja e o backoffice continuam a ler a resposta como antes.
"""
from __future__ import annotations

from typing import Any, get_args

from pydantic_core import core_schema

_PYDANTIC_TYPES = frozenset(get_args(core_schema.ErrorType))
_LOCATIONS = frozenset({"body", "query", "path", "header", "cookie"})

# Como cada campo se diz numa frase: «Indique o nome.», «O nome: mínimo de 2 caracteres.»
_FIELDS = {
    "nome": "o nome",
    "email": "o email",
    "contacto": "o telefone",
    "empresa": "a empresa",
    "nif": "o NIF",
    "localidade": "a localidade",
    "tipo_cliente": "o tipo de cliente",
    "observacoes": "as observações",
    "assunto": "o assunto",
    "mensagem": "a mensagem",
    "linhas": "as linhas do pedido",
    "ean": "o EAN",
    "numero_cor": "a cor",
    "quantidade": "a quantidade",
    "altura": "a altura",
    "referencia_cliente": "o cliente",
}

_EMAIL_EXAMPLE = "Indique um email válido, por exemplo nome@empresa.pt."


def _chars(n: Any) -> str:
    return f"{n} caractere" if n == 1 else f"{n} caracteres"


def _message(err: dict[str, Any], field: str) -> str:
    kind = str(err.get("type") or "")
    text = str(err.get("msg") or "")
    ctx = err.get("ctx") or {}
    label = _FIELDS.get(field) or (f"o campo «{field}»" if field else "o valor")
    head = label[0].upper() + label[1:]

    if kind == "missing":
        return f"Indique {label}."
    if kind == "string_too_short":
        return f"{head}: mínimo de {_chars(ctx.get('min_length'))}."
    if kind == "string_too_long":
        return f"{head}: máximo de {_chars(ctx.get('max_length'))}."
    if kind == "too_short":
        return f"{head}: indique pelo menos {ctx.get('min_length')}."
    if kind == "too_long":
        return f"{head}: máximo de {ctx.get('max_length')}."
    if kind == "string_pattern_mismatch":
        return f"{head}: formato inválido."
    if kind in ("literal_error", "enum"):
        return f"{head}: valor não permitido."
    if kind in ("int_parsing", "int_type", "int_from_float", "int_parsing_size", "float_parsing", "float_type",
                "decimal_parsing", "decimal_type", "finite_number"):
        return f"{head}: indique um número válido."
    if kind == "greater_than_equal":
        return f"{head}: mínimo de {ctx.get('ge')}."
    if kind == "less_than_equal":
        return f"{head}: máximo de {ctx.get('le')}."
    if kind == "greater_than":
        return f"{head}: tem de ser superior a {ctx.get('gt')}."
    if kind == "less_than":
        return f"{head}: tem de ser inferior a {ctx.get('lt')}."
    if kind in ("uuid_parsing", "uuid_type", "uuid_version"):
        return "Identificador inválido."
    if kind in ("bool_parsing", "bool_type"):
        return f"{head}: indique sim ou não."
    if kind == "extra_forbidden":
        return f"{head}: campo não permitido."
    if kind in ("json_invalid", "json_type"):
        return "O pedido não está bem formado."
    if kind == "value_error":
        # `EmailStr` e `ValueError` escritos no código: o texto do código já está em português.
        if "valid email address" in text:
            return _EMAIL_EXAMPLE
        return text.removeprefix("Value error, ")
    if kind == "assertion_error":
        return text.removeprefix("Assertion failed, ")
    if kind in _PYDANTIC_TYPES:
        return f"{head}: valor inválido."
    return text  # erro escrito no código (PydanticCustomError): a mensagem já é a que se quer mostrar


def pt_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Os erros de `RequestValidationError.errors()` em português, sem `input`, `ctx` nem `url`."""
    out = []
    for err in errors:
        loc = list(err.get("loc") or [])
        field = next((p for p in reversed(loc) if isinstance(p, str) and p not in _LOCATIONS), "")
        out.append({"type": err.get("type", ""), "loc": loc, "msg": _message(err, field)})
    return out
