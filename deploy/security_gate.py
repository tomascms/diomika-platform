#!/usr/bin/env python3
"""Security gate institucional — único entrypoint CI/ops.

Corre todas as verificações de segurança de código (sem rede obrigatória).
Exit 1 se alguma falhar.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS: list[tuple[str, list[str]]] = [
    ("route guards", [sys.executable, "deploy/verify_route_guards.py"]),
    ("sensitive route inventory", [sys.executable, "deploy/validate_sensitive_routes.py", "--static"]),
    ("ssrf coverage", [sys.executable, "deploy/verify_ssrf_coverage.py"]),
    ("env separation rules", [sys.executable, "deploy/verify_env_separation.py"]),
    ("csp storefront", [sys.executable, "deploy/verify_csp.py"]),
    ("codebase check", [sys.executable, "deploy/check.py", "--codebase"]),
]


def main() -> int:
    print("=== Diomika SECURITY GATE ===\n")
    env = {**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "backend-api")}
    failed: list[str] = []
    for name, cmd in CHECKS:
        print(f"--- {name} ---")
        proc = subprocess.run(cmd, cwd=ROOT, env=env)
        if proc.returncode != 0:
            failed.append(name)
        print()
    if failed:
        print(f"GATE FAIL: {', '.join(failed)}")
        return 1
    print("GATE OK — todas as verificações de segurança de código passaram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
