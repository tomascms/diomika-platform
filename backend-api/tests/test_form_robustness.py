"""Task 2.3: worker de email e formulários (API-06, API-07, API-13, API-14, API-11, API-12)."""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.test_email_worker_imap import FakeImap
from workers import email_worker, outbox_worker


def _mail(subject: str, sender: str = "Cliente <cliente@exemplo.pt>") -> bytes:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg.set_content("Corpo")
    return msg.as_bytes()


def _async_result(value):
    async def fn(**_k):
        return value

    return fn


# --- API-06 ---------------------------------------------------------------------------------------


def test_worker_downloads_with_peek_so_notifications_stay_unread():
    imap = FakeImap({"5": _mail("[Diomika] Contacto — x [Ref: #abcd1234]", "Caixa <dono@exemplo.pt>")})
    with patch.object(email_worker, "_resolve_message_id", return_value="abcd1234-0000"):
        email_worker._process_folder(imap, "INBOX", set())
    assert imap.fetch_specs == ["(BODY.PEEK[])"]  # RFC822 marcaria \Seen
    assert imap.stored == []  # a notificação ignorada não é marcada como lida


def test_recorded_reply_is_still_marked_seen():
    imap = FakeImap({"6": _mail("Re: pedido [Ref: #abcd1234]")})
    with patch.object(email_worker, "_resolve_message_id", return_value="abcd1234-0000"), patch.object(
        email_worker, "_record_message", return_value=True
    ):
        email_worker._process_folder(imap, "INBOX", set())
    assert imap.stored == [("6", "+FLAGS", r"\Seen")]


def test_successful_cycle_writes_the_heartbeat_the_stale_alert_reads(tmp_path, monkeypatch):
    """Pina o escritor do heartbeat (alimenta o alerta «Worker de email parado» e /health/ready)."""
    for name, value in (("IMAP_SERVER", "imap.test"), ("MAIL_USERNAME", "u"), ("MAIL_PASSWORD", "p")):
        monkeypatch.setattr(email_worker, name, value)
    monkeypatch.setattr(email_worker, "BACKEND_ROOT", tmp_path)
    with patch.object(email_worker, "_load_state", return_value=set()), patch.object(
        email_worker, "_save_state"
    ), patch.object(email_worker.imaplib, "IMAP4_SSL", return_value=MagicMock()), patch.object(
        email_worker, "_process_folder", return_value=0
    ), patch.object(email_worker, "_find_sent_folder", return_value=None):
        email_worker.process_inbox()
    last = json.loads((tmp_path / "data" / ".email_worker_heartbeat.json").read_text(encoding="utf-8"))["last_poll"]
    assert (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() < 5


# --- API-13 ---------------------------------------------------------------------------------------


def _outbox(payload, event_type="contact_notification"):
    return {"id": "e" * 36, "event_type": event_type, "payload": payload, "attempts": 0, "max_attempts": 5}


def test_outbox_contact_notification_leaves_email_pendente():
    db = MagicMock()
    payload = {"notify_to": "a@b.pt", "subject": "s", "body": "b", "message_id": "m-1"}
    with patch.object(outbox_worker, "send_email_async", _async_result(True)), patch.object(
        outbox_worker, "mark_done"
    ) as done, patch("core.database.get_db", return_value=db):
        asyncio.run(outbox_worker.process_event(_outbox(payload)))
    db.table.assert_called_with("contact_messages")
    db.table.return_value.update.assert_called_once_with({"status": "Nova"})
    first_eq = db.table.return_value.update.return_value.eq
    first_eq.assert_called_once_with("id", "m-1")
    first_eq.return_value.eq.assert_called_once_with("status", "Email pendente")  # não pisa «Em conversa»
    done.assert_called_once()


def test_outbox_contact_failure_does_not_touch_status():
    db = MagicMock()
    payload = {"notify_to": "a@b.pt", "subject": "s", "body": "b", "message_id": "m-1"}
    with patch.object(outbox_worker, "send_email_async", _async_result(False)), patch.object(
        outbox_worker, "mark_done"
    ) as done, patch.object(outbox_worker, "mark_failed") as failed, patch("core.database.get_db", return_value=db):
        asyncio.run(outbox_worker.process_event(_outbox(payload)))
    db.table.assert_not_called()
    done.assert_not_called()
    failed.assert_called_once()


# --- API-07 ---------------------------------------------------------------------------------------


def test_idempotency_lock_outlives_a_slow_smtp_send():
    from core import idempotency

    # SMTP: 3 tentativas de 30 s + 1 s + 2 s de espera = 93 s; a loja repete aos 25 s com a mesma chave.
    assert idempotency._STALE_PROCESSING_SECONDS >= 120


# --- API-14 ---------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    import main

    return TestClient(main.app, base_url="http://localhost")


def test_catalog_responses_carry_a_validator_and_answer_304(client):
    first = client.get("/catalogo/meta")
    assert first.status_code == 200
    etag = first.headers["etag"]
    assert etag.startswith('W/"') and first.headers["cache-control"] == "no-cache"

    again = client.get("/catalogo/meta", headers={"If-None-Match": etag})
    assert again.status_code == 304 and again.content == b"" and again.headers["etag"] == etag

    other = client.get("/catalogo/meta", headers={"If-None-Match": 'W/"x"'})
    assert other.status_code == 200


def test_etag_changes_with_the_catalog_version_and_the_query(client):
    from core.cache import bump_catalog_version

    a = client.get("/catalogo/meta").headers["etag"]
    assert client.get("/catalogo/meta?x=1").headers["etag"] != a
    time.sleep(0.002)
    bump_catalog_version()
    assert client.get("/catalogo/meta").headers["etag"] != a


def test_non_catalog_paths_have_no_etag(client):
    assert "etag" not in client.get("/health/live").headers


def test_health_detail_exposes_the_build_commit():
    from core import health

    with patch.object(health, "GIT_SHA", "abc1234"), patch.object(health, "_db_ping", return_value=True), patch.object(
        health, "_outbox_pending_cached", return_value=0
    ):
        assert health.build_health(detailed=True)["git_sha"] == "abc1234"


# --- API-11 ---------------------------------------------------------------------------------------


def test_dead_rate_limiting_layer_is_gone():
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("core.rate_limiting")


def test_bot_and_rate_limit_rejections_share_one_json_format(client):
    blocked = client.get("/health/live", headers={"User-Agent": "Scrapy/2.11"})
    assert blocked.status_code == 403 and blocked.json() == {"detail": "Acesso negado"}

    from core import rate_limit

    with patch.object(rate_limit, "_record_and_check", return_value=False):
        limited = client.get("/categorias")
    assert limited.status_code == 429 and limited.json() == {"detail": "Demasiados pedidos"}
    assert "x-ratelimit-remaining" not in limited.headers


def test_bot_list_is_short_and_keeps_real_tools():
    from core.bot_defense import BLOCKED_BOT_PATTERNS, is_bot_user_agent

    assert len(BLOCKED_BOT_PATTERNS) < 30
    for ua in ("HTTrack/3.0", "Python-urllib/3.12", "Wget/1.21", "sqlmap/1.7"):
        assert is_bot_user_agent(ua) is True
    for ua in ("Mozilla/5.0 (restaurateur) Safari", "Korean Notepad Browser Safari/537"):
        assert is_bot_user_agent(ua) is False  # padrões inventados já não bloqueiam visitantes


# --- API-12 ---------------------------------------------------------------------------------------


def test_saga_and_outbox_are_kept_by_decision():
    """API-12: retirar a saga/outbox custa mais do que o ganho (decisão registada no relatório do lote B5)."""
    from core.saga import contact_saga, orcamento_saga

    assert callable(contact_saga.run_contact_submission_saga)
    assert callable(orcamento_saga.run_orcamento_submission_saga)


def test_heartbeat_lives_in_the_writable_data_folder_for_writer_and_reader(tmp_path, monkeypatch):
    """I-1: o contentor corre sem root e só escreve em data/ e logs/; escritor e leitor partilham o caminho."""
    from paths import heartbeat_path

    assert heartbeat_path(tmp_path) == tmp_path / "data" / ".email_worker_heartbeat.json"
    import inspect

    from core import health
    from workers import email_worker

    assert "heartbeat_path" in inspect.getsource(health._worker_status)
    assert "heartbeat_path" in inspect.getsource(email_worker.process_inbox)
