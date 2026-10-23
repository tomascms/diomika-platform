#!/usr/bin/env python3
"""Load test leve do fluxo público (substituto prático do k6).

Uso:
  python deploy/load/load_test.py --url https://api.diomika.com --concurrency 20 --requests 200
"""
from __future__ import annotations

import argparse
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


UA = "Mozilla/5.0 (compatible; DiomikaLoadTest/1.0)"


def one(url: str, timeout: float) -> tuple[bool, float, int]:
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read(256)
            return True, (time.perf_counter() - t0) * 1000, r.status
    except urllib.error.HTTPError as exc:
        return False, (time.perf_counter() - t0) * 1000, int(exc.code)
    except Exception:
        return False, (time.perf_counter() - t0) * 1000, 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True, help="Base API, ex: https://api.diomika.com")
    p.add_argument("--concurrency", type=int, default=10)
    p.add_argument("--requests", type=int, default=100)
    p.add_argument("--timeout", type=float, default=15.0)
    args = p.parse_args()
    base = args.url.rstrip("/")
    paths = [f"{base}/health", f"{base}/categorias", f"{base}/catalogo/meta"]
    targets = [paths[i % len(paths)] for i in range(args.requests)]

    ok = 0
    times: list[float] = []
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        futs = [pool.submit(one, u, args.timeout) for u in targets]
        for fut in as_completed(futs):
            success, ms, _st = fut.result()
            times.append(ms)
            if success:
                ok += 1
    elapsed = time.perf_counter() - t0
    times_sorted = sorted(times)
    p95 = times_sorted[int(0.95 * (len(times_sorted) - 1))] if times_sorted else 0
    print(f"ok={ok}/{args.requests}  rps={args.requests/elapsed:.1f}  p50={statistics.median(times):.0f}ms  p95={p95:.0f}ms")
    fail_rate = 1 - (ok / max(1, args.requests))
    return 1 if fail_rate > 0.05 else 0


if __name__ == "__main__":
    raise SystemExit(main())
