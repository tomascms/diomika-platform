"""Testes de manutenção idempotency."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_purge_expired_returns_zero_when_empty():
    from core.idempotency_maintenance import purge_expired_idempotency_keys

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.lt.return_value.execute.return_value = MagicMock(count=0)

    with patch("core.idempotency_maintenance.get_db", return_value=mock_db):
        assert purge_expired_idempotency_keys() == 0


def test_purge_expired_deletes_when_found():
    from core.idempotency_maintenance import purge_expired_idempotency_keys

    mock_db = MagicMock()
    chain = mock_db.table.return_value
    chain.select.return_value.lt.return_value.execute.return_value = MagicMock(count=3)
    chain.delete.return_value.lt.return_value.execute.return_value = MagicMock()

    with patch("core.idempotency_maintenance.get_db", return_value=mock_db):
        assert purge_expired_idempotency_keys() == 3
    chain.delete.return_value.lt.assert_called_once()
