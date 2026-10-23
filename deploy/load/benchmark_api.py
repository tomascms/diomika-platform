#!/usr/bin/env python3
"""Baseline rápido de latência API — correr antes/depois de optimizações."""
from __future__ import annotations

import argparse
import statistics
import time
import urllib.request


def sample(url: str, n: int) -> list[float]:
    times: list[float] = []
    headers = {"User-Agent": "DiomikaBenchmark/1.0"}
    for _ in range(n):
        t0 = time.perf_counter()
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read(256)
        times.append(time.perf_counter() - t0)
    return times


def report(label: str, times: list[float]) -> None:
    if not times:
        print(f"{label}: sem dados")
        return
    print(
        f"{label}: n={len(times)} "
        f"p50={statistics.median(times)*1000:.0f}ms "
        f"p95={sorted(times)[int(len(times)*0.95)-1]*1000:.0f}ms "
        f"max={max(times)*1000:.0f}ms"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="https://api.diomika.com")
    parser.add_argument("-n", type=int, default=10)
    args = parser.parse_args()
    base = args.api.rstrip("/")
    report("health", sample(f"{base}/health", args.n))
    report("meta", sample(f"{base}/catalogo/meta", args.n))
    report("categorias", sample(f"{base}/categorias", args.n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
