"""Storage privado — fail-closed (sem fallback público)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_private_signed_url_fails_closed(monkeypatch):
    monkeypatch.setenv("SUPABASE_STORAGE_PRIVATE", "1")
    from utils import storage

    bucket = MagicMock()
    bucket.create_signed_url.return_value = {"signedURL": ""}
    db = MagicMock()
    db.storage.from_.return_value = bucket
    with patch.object(storage, "get_db", return_value=db):
        with pytest.raises(RuntimeError):
            storage.get_signed_url("a/b.png")


def test_upload_rejects_bad_extension(monkeypatch):
    monkeypatch.delenv("SUPABASE_STORAGE_PRIVATE", raising=False)
    from utils.storage import upload_bytes

    with pytest.raises(ValueError):
        upload_bytes(b"x", "evil.exe")


def test_trusted_proxy_cidr(monkeypatch):
    monkeypatch.setenv("TRUST_PROXY", "1")
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "172.16.0.0/12,127.0.0.1")
    from core.rate_limit import _peer_is_trusted_proxy

    class Req:
        client = type("C", (), {"host": "172.18.0.5"})()
        headers = {"x-forwarded-for": "203.0.113.9"}

    assert _peer_is_trusted_proxy(Req())
