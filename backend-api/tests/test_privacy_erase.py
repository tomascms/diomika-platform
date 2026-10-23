"""Privacy erase — só role admin."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


def test_erase_requires_admin_role():
    from routes.privacy import EraseBody, erase_by_email

    body = EraseBody(email="victim@example.com", confirm="ERASE")
    request = MagicMock()
    request.state.api_actor = "catalog-user"
    request.state.request_id = "t"

    with pytest.raises(HTTPException) as exc:
        erase_by_email(body, request, role="catalog")
    assert exc.value.status_code == 403


def test_erase_admin_ok():
    from routes.privacy import EraseBody, erase_by_email

    body = EraseBody(email="victim@example.com", confirm="ERASE")
    request = MagicMock()
    request.state.api_actor = "admin"
    request.state.request_id = "t"

    mock_db = MagicMock()
    chain = mock_db.table.return_value.delete.return_value.eq.return_value
    chain.execute.return_value = MagicMock(data=[])

    with patch("routes.privacy.get_db", return_value=mock_db):
        with patch("routes.privacy.log_admin_action"):
            out = erase_by_email(body, request, role="admin")
    assert out["ok"] is True
    assert out["email"] == "victim@example.com"
