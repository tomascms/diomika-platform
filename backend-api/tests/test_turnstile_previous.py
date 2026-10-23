"""A chave Turnstile anterior continua aceite durante a troca de widget."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from utils import turnstile


def _settings():
    return SimpleNamespace(is_production=True, is_beta=False, _turnstile_is_test_key=lambda: False)


def _fake_post(valid_secret):
    def post(url, data, **kw):
        return SimpleNamespace(json=lambda: {"success": data["secret"] == valid_secret})
    return post


@pytest.mark.parametrize("valid, ok", [("new", True), ("old", True), ("other", False)])
def test_primary_then_previous(monkeypatch, valid, ok):
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "new")
    monkeypatch.setenv("TURNSTILE_SECRET_KEY_PREVIOUS", "old")
    with patch.object(turnstile, "get_settings", _settings), patch.object(turnstile.requests, "post", _fake_post(valid)):
        if ok:
            turnstile.verify_turnstile("tok")
        else:
            with pytest.raises(ValueError):
                turnstile.verify_turnstile("tok")


def test_previous_not_used_when_unset(monkeypatch):
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "new")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY_PREVIOUS", raising=False)
    with patch.object(turnstile, "get_settings", _settings), patch.object(turnstile.requests, "post", _fake_post("old")):
        with pytest.raises(ValueError):
            turnstile.verify_turnstile("tok")
