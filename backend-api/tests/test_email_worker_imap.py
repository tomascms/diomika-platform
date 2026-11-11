"""Worker de email: só descarrega mensagens ainda não processadas (antes: as últimas 50 de cada
pasta a cada 30 s, ~2 GB/dia de IMAP). Também: ligação IMAP com timeout e alerta quando o
heartbeat pára (API-01: esteve ~4 dias parado numa leitura sem timeout, sem ninguém saber)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from unittest.mock import patch

from core import background_workers, health
from workers import email_worker


class FakeImap:
    def __init__(self, messages: dict[str, bytes]):
        self.messages = messages
        self.fetched: list[str] = []
        self.fetch_specs: list[str] = []
        self.stored: list[tuple] = []

    def select(self, *_a, **_k):
        return "OK", [b""]

    def uid(self, command, *args):
        if command == "SEARCH":
            return "OK", [" ".join(self.messages).encode()]
        if command == "FETCH":
            uid = args[0]
            self.fetched.append(uid)
            self.fetch_specs.append(args[1])
            return "OK", [(f"{uid} (UID {uid} BODY[]".encode(), self.messages[uid]), b")"]
        if command == "STORE":
            self.stored.append(args)
        return "OK", [b""]


def _mail(subject: str) -> bytes:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "Cliente <cliente@exemplo.pt>"
    msg.set_content("Resposta do cliente")
    return msg.as_bytes()


def test_processed_messages_are_not_downloaded_again():
    imap = FakeImap({"10": _mail("Re: pedido [Ref: #abcd1234]"), "11": _mail("Re: outro [Ref: #abcd1234]")})
    processed = {"INBOX:10"}
    with patch.object(email_worker, "_resolve_message_id", return_value="abcd1234-0000"), patch.object(
        email_worker, "_record_message", return_value=True
    ):
        email_worker._process_folder(imap, "INBOX", processed)
    assert imap.fetched == ["11"]


def test_message_without_valid_ref_is_marked_processed():
    imap = FakeImap({"20": _mail("Ref: # sem código")})
    processed: set[str] = set()
    email_worker._process_folder(imap, "INBOX", processed)
    assert "INBOX:20" in processed
    imap.fetched.clear()
    email_worker._process_folder(imap, "INBOX", processed)
    assert imap.fetched == []


def test_imap_connect_uses_timeout(monkeypatch):
    for name, value in (("IMAP_SERVER", "imap.test"), ("IMAP_PORT", 993), ("MAIL_USERNAME", "u"), ("MAIL_PASSWORD", "p")):
        monkeypatch.setattr(email_worker, name, value)
    with patch.object(email_worker, "_load_state", return_value=set()), patch.object(
        email_worker.imaplib, "IMAP4_SSL", side_effect=TimeoutError("timed out")
    ) as connect:
        email_worker.process_inbox()  # o timeout cai no except existente: não propaga, o ciclo seguinte volta a ligar
    connect.assert_called_once_with("imap.test", 993, timeout=30)


def _run_loop(monkeypatch, tmp_path, ages_min):
    """Corre o `_maintenance_loop` real, uma volta por item de `ages_min` (idade do heartbeat em
    minutos; None = ainda sem ficheiro). Devolve (alertas acumulados no fim de cada volta, alertas)."""
    monkeypatch.setattr(health, "BACKEND_ROOT", tmp_path)  # onde o /health e o loop lêem o heartbeat
    heartbeat = tmp_path / "data" / ".email_worker_heartbeat.json"
    heartbeat.parent.mkdir(exist_ok=True)
    pending, alerts, per_turn = list(ages_min), [], []

    def write_next_heartbeat():
        age = pending.pop(0)
        if age is None:
            heartbeat.unlink(missing_ok=True)
            return
        last_poll = datetime.now(timezone.utc) - timedelta(minutes=age)
        heartbeat.write_text(json.dumps({"last_poll": last_poll.isoformat(), "recorded": 0}), encoding="utf-8")

    class Turns:  # no lugar de `_stop`: sem esperas, uma volta por item
        def is_set(self):
            if not pending:
                return True
            write_next_heartbeat()
            return False

        def wait(self, _timeout):
            per_turn.append(len(alerts))

    monkeypatch.setattr(background_workers, "_stop", Turns())
    with patch("core.alerts.send_alert", side_effect=lambda *a, **k: alerts.append((a, k))), patch(
        "core.saga.maintenance.sweep_zombie_sagas", return_value=0
    ), patch("core.idempotency_maintenance.purge_expired_idempotency_keys", return_value=0), patch(
        "core.retention.purge_expired_pii"
    ):
        background_workers._maintenance_loop()
    return per_turn, alerts


def test_stale_heartbeat_alerts_once(monkeypatch, tmp_path):
    per_turn, alerts = _run_loop(monkeypatch, tmp_path, [11, 11])
    assert per_turn == [1, 1]  # a 2.ª volta, ainda parado, não repete
    (title,), kwargs = alerts[0]
    assert "email" in title.lower()
    assert kwargs["severity"] == "critical"
    assert "last_poll" in kwargs["detail"]


def test_fresh_heartbeat_no_alert(monkeypatch, tmp_path):
    per_turn, _ = _run_loop(monkeypatch, tmp_path, [1, 1])
    assert per_turn == [0, 0]


def test_missing_heartbeat_no_alert(monkeypatch, tmp_path, caplog):
    # Contentor acabado de criar: o ficheiro só aparece no 1.º ciclo IMAP concluído (todos os deploys).
    per_turn, _ = _run_loop(monkeypatch, tmp_path, [None, None])
    assert per_turn == [0, 0]
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]  # um ERROR viraria evento no Sentry


def test_alert_rearms_after_recovery(monkeypatch, tmp_path):
    per_turn, _ = _run_loop(monkeypatch, tmp_path, [11, 1, 11])
    assert per_turn == [1, 1, 2]  # parou, recuperou, parou outra vez → 2 episódios, 2 alertas
