"""Identificadores nas rotas (SEG-04, API-09): um id que não é UUID nunca chega à base de dados.

Antes, `id_modelo: str` ia direto para o Postgres, que recusava «nao-e-uuid» (22P02); o `except Exception` da
rota registava um erro (um evento no Sentry por pedido) e devolvia 500, ou, noutra rota, um `[]` guardado em cache.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator


def _canonical_uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError:
        raise ValueError("Identificador inválido.") from None


# `id_modelo: UuidStr`: o FastAPI responde 422 (em português, ver core/validation_messages.py) antes de a rota
# correr, e dentro da rota o id chega em texto canónico (minúsculas), como as chaves de cache e os `.eq("id", …)`
# esperam. Para um parâmetro opcional: `UuidStr | None = None`.
UuidStr = Annotated[str, AfterValidator(_canonical_uuid)]
