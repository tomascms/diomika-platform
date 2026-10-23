"""Métricas Prometheus mínimas (texto 0.0.4), sem dependências.

Etiquetas pelo template da rota (`/catalogo/{tipo}/...`), nunca pelo caminho real, para a
cardinalidade não crescer com IDs/slugs. Por processo (1 worker uvicorn).
"""
from __future__ import annotations

import threading
import time
from collections import Counter

_lock = threading.Lock()
_requests: Counter[tuple[str, str, str]] = Counter()
_duration_sum: Counter[tuple[str, str]] = Counter()
_started = time.time()


def observe(method: str, route: str, status: int, seconds: float) -> None:
    code_class = f"{status // 100}xx"
    with _lock:
        _requests[(method, route, code_class)] += 1
        _duration_sum[(method, route)] += seconds


def _rss_bytes() -> int:
    try:
        with open("/proc/self/status", encoding="ascii") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        pass
    return 0


def _esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def render() -> str:
    with _lock:
        reqs = dict(_requests)
        sums = dict(_duration_sum)
    lines = [
        "# HELP diomika_http_requests_total Pedidos HTTP por rota e classe de estado.",
        "# TYPE diomika_http_requests_total counter",
    ]
    for (method, route, code), n in sorted(reqs.items()):
        lines.append(f'diomika_http_requests_total{{method="{method}",route="{_esc(route)}",code="{code}"}} {n}')
    lines += [
        "# HELP diomika_http_request_duration_seconds_sum Tempo total de resposta por rota.",
        "# TYPE diomika_http_request_duration_seconds_sum counter",
    ]
    for (method, route), s in sorted(sums.items()):
        lines.append(f'diomika_http_request_duration_seconds_sum{{method="{method}",route="{_esc(route)}"}} {s:.6f}')
    lines += [
        "# HELP process_resident_memory_bytes Memória residente do processo.",
        "# TYPE process_resident_memory_bytes gauge",
        f"process_resident_memory_bytes {_rss_bytes()}",
        "# HELP process_uptime_seconds Segundos desde o arranque.",
        "# TYPE process_uptime_seconds gauge",
        f"process_uptime_seconds {time.time() - _started:.0f}",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    observe("GET", "/categorias", 200, 0.01)
    observe("POST", "/contacto", 503, 0.2)
    out = render()
    assert 'route="/categorias",code="2xx"} 1' in out and 'code="5xx"} 1' in out
    print(out)
