"""Task 2.1: o event loop fica livre nas rotas de formulário, os alertas não bloqueiam nem repetem, o health é honesto."""
from __future__ import annotations

import asyncio
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from core import alerts, health


def _slow(value=None, delay=0.2):
    def fn(*_a, **_k):
        time.sleep(delay)  # ida e volta à Supabase
        return value

    return fn


async def _async_noop(*_a, **_k):
    return None


async def _with_ticker(coro_factory) -> int:
    ticks = 0

    async def ticker():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    task = asyncio.create_task(ticker())
    await coro_factory()
    task.cancel()
    return ticks


# --- API-03: rotas async com BD lenta ---------------------------------------------------------------


def test_orcamento_route_keeps_event_loop_free():
    from routes import orcamentos

    body = orcamentos.OrcamentoRequest(
        nome="Ana Silva",
        email="ana@example.com",
        linhas=[{"ean": "5601234567890", "numero_cor": 1, "quantidade": 12}],
    )

    async def fake_saga(*_a, **_k):
        return MagicMock(pedido_id="p1", status="Nova")

    async def call():
        with patch.object(orcamentos, "get_cached_response", _slow(None)), patch.object(
            orcamentos, "begin_idempotent_request", _slow("proceed")
        ), patch.object(orcamentos, "validate_order_lines", _slow(None)), patch.object(
            orcamentos, "complete_idempotent_request", _slow(None)
        ), patch.object(orcamentos, "run_orcamento_submission_saga", fake_saga), patch.object(
            orcamentos, "rate_limit"
        ), patch("utils.turnstile.verify_turnstile_async", _async_noop):
            out = await orcamentos.submit_orcamento(body, MagicMock(), idempotency_key="k1")
        assert out["id"] == "p1"

    # 4 chamadas de 0,2 s: com o loop livre o ticker corre dezenas de vezes; bloqueado, ~0.
    assert asyncio.run(_with_ticker(call)) > 30


def test_contact_route_keeps_event_loop_free_and_checks_turnstile_before_the_key():
    from routes import contact

    msg = contact.ContactRequest(nome="Ana", email="ana@example.com", mensagem="Olá, queria saber preços.")
    order: list[str] = []

    async def fake_saga(*_a, **_k):
        return MagicMock(email_sent=True, status="Nova")

    def begin(*_a, **_k):
        order.append("begin")
        time.sleep(0.2)
        return "proceed"

    async def turnstile(*_a, **_k):
        order.append("turnstile")

    async def call():
        with patch.object(contact, "get_cached_response", _slow(None)), patch.object(
            contact, "begin_idempotent_request", begin
        ), patch.object(contact, "complete_idempotent_request", _slow(None)), patch.object(
            contact, "run_contact_submission_saga", fake_saga
        ), patch.object(contact, "rate_limit"), patch.object(contact, "verify_turnstile_async", turnstile):
            await contact.send_message(msg, MagicMock(), idempotency_key="k1")

    assert asyncio.run(_with_ticker(call)) > 20
    assert order == ["turnstile", "begin"]  # API-07: falhar o Turnstile não reserva a chave


def test_contact_failed_turnstile_does_not_reserve_the_key():
    from fastapi import HTTPException
    from routes import contact

    msg = contact.ContactRequest(nome="Ana", email="ana@example.com", mensagem="Olá, queria saber preços.")

    async def bad_turnstile(*_a, **_k):
        raise ValueError("Verificação falhou")

    begin = MagicMock()
    with patch.object(contact, "begin_idempotent_request", begin), patch.object(
        contact, "verify_turnstile_async", bad_turnstile
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(contact.send_message(msg, MagicMock(), idempotency_key="k1"))
    assert exc.value.status_code == 400
    begin.assert_not_called()


def test_orcamento_saga_resolves_lines_with_one_catalogue_query():
    from core.saga import orcamento_saga
    from models.schemas import PedidoOrcamentoLinha

    linhas = [PedidoOrcamentoLinha(ean="5601234567890", numero_cor=i, quantidade=12) for i in range(1, 6)]
    calls = []

    def batch(ls):
        calls.append(len(ls))
        return [{**l, "modelo": "M", "dimensoes": "1x1", "cor_nome": "c"} for l in ls]

    with patch.object(orcamento_saga, "resolve_product_lines_batch", batch):
        texts = orcamento_saga._line_texts(linhas)
    assert calls == [5] and len(texts) == 5 and "Cor 3" in texts[2]


# --- API-04 / SEG-17: alertas ----------------------------------------------------------------------


@pytest.fixture
def alert_env(tmp_path, monkeypatch):
    monkeypatch.setattr(alerts, "_ALERT_LOG", tmp_path / "alerts.log")
    monkeypatch.setattr(alerts, "_last_sent", {})
    monkeypatch.setattr(alerts, "_webhook_url", lambda: "https://hooks.example.test/x")
    return tmp_path


def _drain():
    alerts._pool.submit(lambda: None).result(timeout=5)  # 1 só fio: quando isto corre, o resto já correu


def test_alert_webhook_does_not_block_the_caller(alert_env):
    done = []

    def slow_post(url, payload):
        time.sleep(0.5)
        done.append(payload["title"])

    with patch.object(alerts, "_post_webhook", slow_post):
        t0 = time.perf_counter()
        assert alerts.send_alert("Latência elevada") is True
        assert time.perf_counter() - t0 < 0.2  # a rede corre noutro fio
        _drain()
    assert done == ["Latência elevada"]


def test_same_title_is_sent_once_per_window(alert_env):
    sent = []
    with patch.object(alerts, "_post_webhook", lambda url, payload: sent.append(payload["title"])):
        for _ in range(5):
            alerts.send_alert("Admin login falhou")
        alerts.send_alert("Outro título")
        _drain()
    assert sent == ["Admin login falhou", "Outro título"]
    assert len((alert_env / "alerts.log").read_text(encoding="utf-8").splitlines()) == 2


def test_dedupe_window_expires_and_can_be_turned_off(alert_env, monkeypatch):
    sent = []
    clock = {"t": 1000.0}
    monkeypatch.setattr(alerts.time, "monotonic", lambda: clock["t"])
    with patch.object(alerts, "_post_webhook", lambda url, payload: sent.append(1)):
        alerts.send_alert("x")
        alerts.send_alert("x")
        clock["t"] += 601
        alerts.send_alert("x")  # passou a janela
        alerts.send_alert("ep", dedupe_seconds=0)
        alerts.send_alert("ep", dedupe_seconds=0)  # 2.º episódio do vigia: não é engolido
        _drain()
    assert len(sent) == 4


def test_stale_worker_alert_opts_out_of_the_title_window():
    import inspect

    from core import background_workers

    assert "dedupe_seconds=0" in inspect.getsource(background_workers._maintenance_loop)


def test_latency_middleware_alerts_through_send_alert():
    from core.middleware import LatencyAlertMiddleware

    mw = LatencyAlertMiddleware(MagicMock())
    mw.threshold_ms = 1
    request = MagicMock()
    request.url.path = "/catalogo"
    request.method = "GET"

    async def call_next(_r):
        await asyncio.sleep(0.01)
        return "resp"

    with patch("core.alerts.send_alert") as alert:
        assert asyncio.run(mw.dispatch(request, call_next)) == "resp"
    assert alert.call_args.args[0] == "Latência elevada"


# --- SEG-13 / API-15: health -----------------------------------------------------------------------


@pytest.fixture
def fresh_health(monkeypatch, tmp_path):
    monkeypatch.setattr(health, "_ready_cache", {"body": None, "at": 0.0})
    monkeypatch.setattr(health, "BACKEND_ROOT", tmp_path)
    return tmp_path


def _heartbeat(root, minutes_ago):
    from datetime import datetime, timedelta, timezone

    last = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    (root / "data").mkdir(exist_ok=True)
    (root / "data" / ".email_worker_heartbeat.json").write_text(json.dumps({"last_poll": last.isoformat()}), encoding="utf-8")


def test_ready_is_cached_for_ten_seconds(fresh_health):
    pings = []
    with patch.object(health, "_db_ping", lambda: pings.append(1) or True):
        for _ in range(5):
            assert health.build_health(ready=True)["database"] is True
    assert len(pings) == 1


def test_db_ping_honours_its_limit():
    # Antes: `with ThreadPoolExecutor` esperava pela tarefa ao sair (3 s para um limite de 0,5 s).
    fake = MagicMock()
    fake.table.return_value.select.return_value.limit.return_value.execute.side_effect = _slow(None, 1.0)
    with patch.object(health, "get_db", return_value=fake), patch.object(health, "_DB_TIMEOUT_SEC", 0.2):
        t0 = time.perf_counter()
        assert health._db_ping() is False
        assert time.perf_counter() - t0 < 0.7


def test_ready_reports_stale_email_worker_with_503(fresh_health):
    from fastapi.testclient import TestClient

    import main

    _heartbeat(fresh_health, 20)
    with patch.object(health, "_db_ping", lambda: True):
        resp = TestClient(main.app).get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["email_worker_stale"] is True


def test_ready_ok_with_fresh_worker(fresh_health):
    from fastapi.testclient import TestClient

    import main

    _heartbeat(fresh_health, 1)
    with patch.object(health, "_db_ping", lambda: True):
        resp = TestClient(main.app).get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "database": True, "email_worker_stale": False}


def test_pg_ping_is_gone():
    assert not hasattr(health, "_pg_ping")


def test_ntfy_gets_a_readable_message_and_other_webhooks_keep_json():
    from core import alerts

    payload = {"title": "Worker de email parado", "severity": "critical", "detail": {"minutos": 20}, "text": "[x] y"}
    body, headers = alerts.webhook_request("https://ntfy.sh/diomika-alertas", payload)
    assert body == b"minutos: 20" and headers["Title"] == "Worker de email parado" and headers["Priority"] == "urgent"
    body, headers = alerts.webhook_request("https://hooks.slack.com/services/x", payload)
    assert headers["Content-Type"] == "application/json" and b'"title"' in body
