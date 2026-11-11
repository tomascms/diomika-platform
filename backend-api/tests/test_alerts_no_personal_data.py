"""LEGAL-16: os alertas que seguem para o webhook (ntfy.sh, sem acordo do art. 28.º) não levam IP nem nome de utilizador."""
from __future__ import annotations

import json
from collections import defaultdict
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

IP = "203.0.113.9"
USER = "alice"


def _sent(alert: MagicMock) -> str:
    """Tudo o que o alerta diz (título e detalhe), como texto, para procurar dados pessoais."""
    return json.dumps([alert.call_args.args, alert.call_args.kwargs], default=str)


@pytest.fixture()
def user_store(tmp_path, monkeypatch):
    monkeypatch.setattr("core.admin_users._STORE", tmp_path / "admin_users.json")


def test_failed_login_alert_has_no_ip_or_username(user_store):
    from core.admin_users import upsert_user
    from routes.admin_auth import LoginBody, login

    upsert_user(USER, "Password-Ok-99x!", role="admin")
    request = MagicMock()
    request.state.request_id = "t"

    with patch("routes.admin_auth.rate_limit"), patch("routes.admin_auth.rate_limit_absolute"), patch(
        "routes.admin_auth.get_client_ip", return_value=IP
    ), patch("routes.admin_auth.log_admin_action") as audit, patch("routes.admin_auth.send_alert") as alert:
        with pytest.raises(HTTPException) as exc:
            login(LoginBody(username=USER, password="wrong-password"), request)

    assert exc.value.status_code == 401
    alert.assert_called_once()
    assert IP not in _sent(alert) and USER not in _sent(alert)
    # O registo de auditoria (conservado 12 meses, na política) continua a ter quem e de onde.
    assert audit.call_args.kwargs["actor"] == USER and audit.call_args.kwargs["client_ip"] == IP


def test_brute_force_alert_has_no_ip_or_username(monkeypatch):
    from core import anomaly

    monkeypatch.setenv("ANOMALY_LOGIN_FAIL_THRESHOLD", "2")
    monkeypatch.setattr(anomaly, "_login_fails", defaultdict(list))
    monkeypatch.setattr(anomaly, "_last_alert", {})

    with patch.object(anomaly, "send_alert") as alert:
        anomaly.note_login_failure(USER, IP)
        alert.assert_not_called()  # uma falha só não alerta
        anomaly.note_login_failure(USER, IP)

    alert.assert_called_once()
    assert alert.call_args.kwargs["detail"]["fails"] == 2  # o alerta continua útil: diz quantas falhas
    assert IP not in _sent(alert) and USER not in _sent(alert)


def test_password_changed_alert_has_no_username():
    from routes.admin_auth import ChangePasswordBody, change_own_password

    request = MagicMock()
    request.state.api_actor = USER
    request.state.request_id = "t"
    body = ChangePasswordBody(current_password="old-password-1", new_password="new-password-12345")

    with patch("routes.admin_auth.change_password"), patch(
        "routes.admin_auth.get_client_ip", return_value=IP
    ), patch("routes.admin_auth.log_admin_action"), patch("routes.admin_auth.send_alert") as alert:
        assert change_own_password(body, request, role="admin") == {"ok": True, "relogin_required": True}

    alert.assert_called_once()
    assert USER not in _sent(alert)
