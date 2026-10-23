"""Admin/system: loopback ou desktop gate."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException


def test_admin_local_allows_loopback_in_production(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.delenv("DIOMIKA_BETA", raising=False)
    monkeypatch.delenv("DIOMIKA_DESKTOP_GATE", raising=False)
    from core.config import get_settings
    from core.local_only import admin_must_be_local

    get_settings.cache_clear()
    req = MagicMock()
    req.client.host = "127.0.0.1"
    req.headers = {}
    admin_must_be_local(req)
    get_settings.cache_clear()


def test_admin_local_blocks_remote_without_gate(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.delenv("DIOMIKA_BETA", raising=False)
    monkeypatch.delenv("DIOMIKA_DESKTOP_GATE", raising=False)
    from core.config import get_settings
    from core.local_only import admin_must_be_local

    get_settings.cache_clear()
    req = MagicMock()
    req.client.host = "198.51.100.10"
    req.headers = {}
    with pytest.raises(HTTPException) as exc:
        admin_must_be_local(req)
    assert exc.value.status_code == 403
    get_settings.cache_clear()


def test_admin_allows_remote_with_desktop_gate(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.delenv("DIOMIKA_BETA", raising=False)
    monkeypatch.setenv("DIOMIKA_DESKTOP_GATE", "test-desktop-gate-secret-32chars!!")
    from core.config import get_settings
    from core.local_only import admin_must_be_local

    get_settings.cache_clear()
    req = MagicMock()
    req.client.host = "198.51.100.10"
    req.headers = {"x-diomika-desktop": "test-desktop-gate-secret-32chars!!"}
    admin_must_be_local(req)
    get_settings.cache_clear()


def test_admin_local_allows_remote_in_beta(monkeypatch):
    monkeypatch.setenv("DIOMIKA_ENV", "production")
    monkeypatch.setenv("DIOMIKA_BETA", "1")
    from core.config import get_settings
    from core.local_only import admin_must_be_local

    get_settings.cache_clear()
    req = MagicMock()
    req.client.host = "198.51.100.10"
    req.headers = {}
    admin_must_be_local(req)
    get_settings.cache_clear()
