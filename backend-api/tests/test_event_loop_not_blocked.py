"""Submissão de contacto não pode bloquear o event loop (1 worker: bloqueava a API toda)."""
from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

from core.saga import contact_saga


def _slow_db() -> MagicMock:
    db = MagicMock()

    def slow_execute(*_a, **_k):
        time.sleep(0.2)  # ida e volta à Supabase
        return MagicMock(data=[{"id": "x"}])

    db.table.return_value.insert.return_value.execute.side_effect = slow_execute
    db.table.return_value.upsert.return_value.execute.side_effect = slow_execute
    return db


def test_contact_saga_keeps_event_loop_free():
    async def scenario() -> int:
        ticks = 0

        async def ticker():
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        task = asyncio.create_task(ticker())
        with patch.object(contact_saga, "get_db", return_value=_slow_db()), patch(
            "core.saga.logging.get_db", return_value=_slow_db()
        ), patch.object(contact_saga, "contact_notify_email", return_value=None):
            await contact_saga.run_contact_submission_saga({"nome": "a", "email": "a@b.pt"})
        task.cancel()
        return ticks

    # ~4 chamadas de 0,2 s: com o loop livre o ticker corre dezenas de vezes; bloqueado, ~0.
    assert asyncio.run(scenario()) > 20


def test_storefront_filter_names_are_restricted():
    from core.catalog_storefront import _split_filters

    model, product = _split_filters({"cor": "azul", "x->>y": "1", "a,b": "1", "visibilidade)": "false"})
    assert list(model) == ["cor"] and not product
