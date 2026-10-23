#!/usr/bin/env python3
"""Verificação unificada API + loja; envia alerta ntfy/webhook se falhar."""
from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend-api"))
sys.path.insert(0, str(ROOT / "deploy"))

from core.env_loader import load_project_env  # noqa: E402

load_project_env()

UA = "Mozilla/5.0 (compatible; DiomikaMonitor/1.0)"


def fetch(url: str, timeout: float) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read(4096).decode("utf-8", errors="replace")


def check_health(base: str, timeout: float) -> tuple[bool, str]:
    url = base if base.endswith("/health") else f"{base.rstrip('/')}/health"
    try:
        status, body = fetch(url, timeout)
    except Exception as exc:
        return False, f"{url} — {exc}"
    ok = status == 200 and "online" in body
    return ok, f"{url} -> {status}"


def check_ready(base: str, timeout: float) -> tuple[bool, str]:
    root = base.rstrip("/").removesuffix("/health")
    url = f"{root}/health/ready"
    try:
        status, _ = fetch(url, timeout)
    except Exception as exc:
        return False, f"{url} — {exc}"
    return status == 200, f"{url} -> {status}"


def check_site(site: str, timeout: float) -> tuple[bool, str]:
    url = site.rstrip("/") + "/"
    try:
        status, _ = fetch(url, timeout)
    except Exception as exc:
        return False, f"{url} — {exc}"
    return status == 200, f"{url} -> {status}"


def check_with_retries(fn, *, retries: int = 3, delay: float = 2.0) -> tuple[bool, str]:
    last_msg = ""
    for attempt in range(retries):
        ok, msg = fn()
        last_msg = msg
        if ok:
            return True, msg
        if attempt < retries - 1:
            time.sleep(delay)
    return False, last_msg


def send_failure_alert(failures: list[str]) -> None:
    from core.alerts import send_alert

    send_alert(
        "Monitorização: serviço indisponível",
        severity="critical",
        detail={"failures": failures},
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=os.getenv("API_HEALTH_URL") or "https://api.diomika.com")
    parser.add_argument("--site", default=os.getenv("SITE_URL") or "https://www.diomika.com")
    parser.add_argument("--ready", action="store_true", help="Também /health/ready")
    parser.add_argument(
        "--ready-optional",
        action="store_true",
        help="/health/ready informativo — não falha o job se só isto falhar",
    )
    parser.add_argument("--alert", action="store_true", help="Enviar webhook se falhar")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--retries", type=int, default=3, help="Tentativas por check crítico")
    args = parser.parse_args()

    failures: list[str] = []
    for label, fn in (
        ("API", lambda: check_health(args.api, args.timeout)),
        ("Site", lambda: check_site(args.site, args.timeout)),
    ):
        ok, msg = check_with_retries(fn, retries=args.retries)
        print("OK" if ok else "FAIL", msg)
        if not ok:
            failures.append(f"{label}: {msg}")

    if args.ready:
        ok, msg = check_with_retries(lambda: check_ready(args.api, args.timeout), retries=2)
        level = "OK" if ok else ("WARN" if args.ready_optional else "FAIL")
        print(level, msg)
        if not ok and not args.ready_optional:
            failures.append(f"Ready: {msg}")

    if failures:
        if args.alert:
            send_failure_alert(failures)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
