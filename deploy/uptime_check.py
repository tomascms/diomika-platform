#!/usr/bin/env python3
"""Uptime check — API health (+ ready). Exit 1 se falhar.

Uso:
  python deploy/uptime_check.py --url https://api.diomika.com
  python deploy/uptime_check.py --url https://api.diomika.com --ready
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request


UA = "Mozilla/5.0 (compatible; DiomikaUptime/1.0)"


def fetch(url: str, timeout: float) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.getenv("API_HEALTH_URL") or os.getenv("API_BASE_URL") or "")
    parser.add_argument("--ready", action="store_true", help="Também /health/ready")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    base = (args.url or "").rstrip("/")
    if not base:
        print("ERRO: --url ou API_HEALTH_URL em falta")
        return 2
    if base.endswith("/health"):
        health = base
        root = base[: -len("/health")]
    else:
        health = f"{base}/health"
        root = base

    try:
        st, body = fetch(health, args.timeout)
    except Exception as exc:
        print(f"FAIL {health}: {exc}")
        return 1
    ok = st == 200 and ("online" in body or "ready" in body or "ok" in body.lower())
    print(f"{'OK' if ok else 'FAIL'} {health} -> {st} {body[:120]}")
    if not ok:
        return 1

    if args.ready:
        ready = f"{root}/health/ready"
        try:
            st2, body2 = fetch(ready, args.timeout)
        except Exception as exc:
            print(f"FAIL {ready}: {exc}")
            return 1
        ok2 = st2 == 200
        print(f"{'OK' if ok2 else 'FAIL'} {ready} -> {st2} {body2[:120]}")
        if not ok2:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
