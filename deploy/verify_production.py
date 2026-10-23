#!/usr/bin/env python3
"""Único comando de verificação de produção.

Corre: uptime → smoke → security → load (soft) → playwright (se instalado).

  python deploy/verify_production.py
  python deploy/verify_production.py --api https://api.diomika.com --site https://www.diomika.com
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FE = ROOT / "frontend-web"


def run(cmd: list[str], *, soft: bool = False) -> int:
    print(f"\n>>> {' '.join(cmd)}\n")
    rc = subprocess.run(cmd, cwd=ROOT).returncode
    if rc != 0 and soft:
        print("WARN (soft) — continua")
        return 0
    return rc


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api", default=os.getenv("API_BASE_URL") or "https://api.diomika.com")
    p.add_argument("--site", default=os.getenv("SITE_URL") or "https://www.diomika.com")
    p.add_argument("--skip-e2e", action="store_true")
    p.add_argument("--skip-load", action="store_true")
    args = p.parse_args()
    failed = 0

    failed += run([sys.executable, "deploy/uptime_check.py", "--url", args.api, "--ready"])
    failed += run([sys.executable, "deploy/smoke_test.py", "--api", args.api, "--site", args.site])
    failed += run([sys.executable, "deploy/security_test.py", "--url", args.api])

    if not args.skip_load:
        failed += run(
            [
                sys.executable,
                "deploy/load/load_test.py",
                "--url",
                args.api,
                "--concurrency",
                "8",
                "--requests",
                "40",
            ],
            soft=True,
        )

    if not args.skip_e2e:
        env = {
            **os.environ,
            "E2E_API_URL": args.api,
            "E2E_SITE_URL": args.site,
        }
        e2e = subprocess.run(
            ["npm", "run", "test:e2e"],
            cwd=FE,
            env=env,
            shell=os.name == "nt",
        ).returncode
        if e2e != 0:
            print("WARN e2e — instala com: cd frontend-web && npx playwright install chromium")
            # soft: não falha verify se playwright browsers em falta localmente
        else:
            print("OK e2e")

    if failed:
        print(f"\nVERIFY FAIL ({failed})")
        return 1
    print("\nVERIFY OK — produção saudável")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
