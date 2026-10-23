"""Login local, sessões e ACL de negócio."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException


@pytest.fixture()
def user_store(tmp_path, monkeypatch):
    store = tmp_path / "admin_users.json"
    monkeypatch.setattr("core.admin_users._STORE", store)
    return store


def test_password_hash_roundtrip():
    from core.admin_users import hash_password, verify_password

    enc = hash_password("Senha-Forte-123!")
    assert verify_password("Senha-Forte-123!", enc)
    assert not verify_password("outra", enc)


def test_login_lockout(user_store):
    from core.admin_users import authenticate, upsert_user

    upsert_user("alice", "Password-Ok-99x!", role="catalog")
    for _ in range(5):
        user, err = authenticate("alice", "wrong-password")
        assert user is None
        assert err
    user, err = authenticate("alice", "Password-Ok-99x!")
    assert user is None
    assert "bloqueada" in (err or "").lower()


def test_session_issue_and_parse(monkeypatch):
    monkeypatch.setenv("API_SECRET_KEY", "k" * 40)
    from core import session_tokens
    import importlib

    importlib.reload(session_tokens)
    token, ttl = session_tokens.issue_session(username="bob", role="pedidos")
    assert ttl > 0
    sess = session_tokens.parse_session(token)
    assert sess["username"] == "bob"
    assert sess["role"] == "pedidos"
    session_tokens.revoke_session(token)
    assert session_tokens.parse_session(token) is None


def test_new_login_invalidates_previous_session(monkeypatch):
    monkeypatch.setenv("API_SECRET_KEY", "k" * 40)
    from core import session_tokens
    import importlib

    importlib.reload(session_tokens)
    t1, _ = session_tokens.issue_session(username="carol", role="catalog")
    t2, _ = session_tokens.issue_session(username="carol", role="catalog")
    assert session_tokens.parse_session(t2) is not None
    assert session_tokens.parse_session(t1) is None


def test_session_secret_required(monkeypatch):
    monkeypatch.delenv("API_SECRET_KEY", raising=False)
    monkeypatch.delenv("ADMIN_SESSION_SECRET", raising=False)
    from core import session_tokens
    import importlib

    importlib.reload(session_tokens)
    with pytest.raises(RuntimeError):
        session_tokens.issue_session(username="x", role="admin")


def test_password_strength_rejects_weak():
    from core.admin_users import validate_password_strength

    with pytest.raises(ValueError):
        validate_password_strength("short1")
    with pytest.raises(ValueError):
        validate_password_strength("onlylettersabc")
    with pytest.raises(ValueError):
        validate_password_strength("123456789012")
    with pytest.raises(ValueError):
        validate_password_strength("senha-forte-99")  # sem maiúscula/símbolo
    validate_password_strength("Senha-Forte-99!")


def test_log_redaction():
    from core.log_safe import redact_text

    assert "[redacted]" in redact_text("API_SECRET_KEY=supersecreto123456")
    assert "[redacted]" in redact_text("token=dms1.abc.def")
    assert "[redacted-session]" in redact_text("Authorization Bearer dms1.abc.def")
    assert "ok" in redact_text("status=ok")


def test_role_acl_tables():
    from core.auth import assert_table_action, role_can_access_table

    assert role_can_access_table("catalog", "categories")
    assert not role_can_access_table("catalog", "contact_messages")
    assert role_can_access_table("mensagens", "contact_messages")
    assert not role_can_access_table("admin", "outbox_events")

    with pytest.raises(HTTPException) as exc:
        assert_table_action("outbox_events", "read", "admin")
    assert exc.value.status_code == 403

    assert_table_action("categories", "hard_delete", "catalog")

    with pytest.raises(HTTPException):
        assert_table_action("categories", "hard_delete", "mensagens")


def test_assert_dedicated_mensagens():
    from core.auth import assert_dedicated_access

    assert_dedicated_access("contact_messages", "mensagens")
    assert_dedicated_access("contact_messages", "admin")
    with pytest.raises(HTTPException):
        assert_dedicated_access("contact_messages", "catalog")


def test_disable_user_revokes_sessions(user_store, monkeypatch):
    monkeypatch.setenv("API_SECRET_KEY", "k" * 40)
    from core import session_tokens
    import importlib

    importlib.reload(session_tokens)
    from core.admin_users import authenticate, set_user_disabled, upsert_user

    upsert_user("dave", "Password-Ok-99x!", role="catalog")
    token, _ = session_tokens.issue_session(username="dave", role="catalog")
    assert session_tokens.parse_session(token)
    set_user_disabled("dave", True)
    assert session_tokens.parse_session(token) is None
    user, err = authenticate("dave", "Password-Ok-99x!")
    assert user is None
    assert "desactiv" in (err or "").lower()


def test_idle_timeout_expires_session(monkeypatch):
    monkeypatch.setenv("API_SECRET_KEY", "k" * 40)
    monkeypatch.setenv("ADMIN_SESSION_IDLE_MINUTES", "1")
    monkeypatch.delenv("REDIS_URL", raising=False)
    from core import session_tokens
    from core import rate_limit
    import importlib
    import time

    importlib.reload(rate_limit)
    rate_limit.reset_redis_client()
    rate_limit._redis_next_try = time.time() + 3600  # skip redis during teste
    importlib.reload(session_tokens)
    token, _ = session_tokens.issue_session(username="erin", role="ops")
    assert session_tokens.parse_session(token)
    jti = session_tokens.parse_session(token)["jti"]
    with session_tokens._lock:
        session_tokens._last_seen[jti] = int(time.time()) - 120
    assert session_tokens.parse_session(token) is None


def test_normalize_text_nfc():
    from core.text_safe import normalize_text

    assert normalize_text("  café\x00  ") == "café"
    assert "\x00" not in normalize_text("a\x00b")


def test_upload_rejects_zip_polyglot():
    from utils.image_validation import validate_upload_bytes

    # PNG header + ZIP signature embutido
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20 + b"PK\x03\x04" + b"x" * 100
    with pytest.raises(ValueError, match="embutido"):
        validate_upload_bytes(data, "evil.png")


def test_bootstrap_creates_user_when_store_empty(user_store, monkeypatch):
    monkeypatch.setenv("ADMIN_BOOTSTRAP_USER", "admin")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_PASSWORD", "Bootstrap-Sync-1!")
    monkeypatch.delenv("ADMIN_BOOTSTRAP_SYNC", raising=False)

    from core.admin_users import authenticate, ensure_bootstrap

    ensure_bootstrap()
    user, err = authenticate("admin", "Bootstrap-Sync-1!")
    assert err is None
    assert user and user["username"] == "admin"


def test_bootstrap_sync_updates_password_when_enabled(user_store, monkeypatch):
    from core.admin_users import authenticate, ensure_bootstrap, upsert_user

    upsert_user("admin", "Password-Old-123!", role="admin")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_USER", "admin")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_PASSWORD", "Password-New-456!")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_SYNC", "1")

    ensure_bootstrap()
    user, err = authenticate("admin", "Password-New-456!")
    assert err is None
    assert user and user["username"] == "admin"
    _, err_old = authenticate("admin", "Password-Old-123!")
    assert err_old


def test_bootstrap_sync_skipped_without_flag(user_store, monkeypatch):
    from core.admin_users import authenticate, ensure_bootstrap, upsert_user

    upsert_user("admin", "Password-Old-123!", role="admin")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_USER", "admin")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_PASSWORD", "Password-New-456!")
    monkeypatch.delenv("ADMIN_BOOTSTRAP_SYNC", raising=False)

    ensure_bootstrap()
    user, err = authenticate("admin", "Password-Old-123!")
    assert err is None
    assert user and user["username"] == "admin"
    _, err_new = authenticate("admin", "Password-New-456!")
    assert err_new
