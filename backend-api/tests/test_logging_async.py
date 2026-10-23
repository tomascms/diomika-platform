"""O envio para o Axiom não bloqueia quem regista o log; HEAD /health responde 200."""
from __future__ import annotations

import logging
import time
from unittest.mock import patch

from core import structured_logging as sl


def test_axiom_send_runs_off_the_caller_thread(monkeypatch):
    monkeypatch.setenv("AXIOM_TOKEN", "t")
    root = logging.getLogger()
    before = list(root.handlers)
    monkeypatch.setattr(sl, "_axiom_listener", None)
    slow = lambda *a, **k: time.sleep(0.5)  # noqa: E731
    with patch.object(sl.urllib.request, "urlopen", side_effect=slow), patch(
        "core.ssrf_guard.assert_safe_outbound_url", lambda url: None
    ):
        sl._start_axiom(root)
        try:
            t0 = time.perf_counter()
            for i in range(5):
                logging.getLogger("diomika-test").warning("linha %s", i)
            assert time.perf_counter() - t0 < 0.3
        finally:
            sl._axiom_listener.stop()
            root.handlers[:] = before


def test_head_on_health(client=None):
    from fastapi.testclient import TestClient

    import main

    c = TestClient(main.app, base_url="http://localhost")
    for path in ("/health", "/health/live"):
        assert c.head(path, headers={"User-Agent": "UptimeRobot/2.0"}).status_code == 200
