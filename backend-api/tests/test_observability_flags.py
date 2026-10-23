"""Feature flags + login sem enumeração."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


@pytest.fixture()
def user_store(tmp_path, monkeypatch):
    store = tmp_path / "admin_users.json"
    monkeypatch.setattr("core.admin_users._STORE", store)
    return store


def test_feature_flag_defaults(monkeypatch):
    from core.feature_flags import flag

    monkeypatch.delenv("FEATURE_CONTACT_FORM", raising=False)
    assert flag("CONTACT_FORM", True) is True
    assert flag("CONTACT_FORM", False) is False
    monkeypatch.setenv("FEATURE_CONTACT_FORM", "0")
    assert flag("CONTACT_FORM", True) is False
    monkeypatch.setenv("FEATURE_CONTACT_FORM", "1")
    assert flag("CONTACT_FORM", False) is True


def test_login_error_is_generic(user_store):
    """Cliente nunca vê lockout/disabled/tentativas — só Credenciais inválidas."""
    from core.admin_users import upsert_user
    from routes.admin_auth import LoginBody, login

    upsert_user("alice", "Password-Ok-99x!", role="admin")
    request = MagicMock()
    request.state.request_id = "t"
    body = LoginBody(username="alice", password="wrong-password")

    with patch("routes.admin_auth.rate_limit"), patch("routes.admin_auth.rate_limit_absolute"):
        with patch("routes.admin_auth.get_client_ip", return_value="127.0.0.1"):
            with patch("routes.admin_auth.log_admin_action"), patch("routes.admin_auth.send_alert"):
                with pytest.raises(HTTPException) as exc:
                    login(body, request)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Credenciais inválidas"
