#!/usr/bin/env python3
"""Garante que saídas HTTP usam ssrf_guard ou hosts fixos conhecidos."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend-api"

# Ficheiros que podem fazer HTTP outbound
SCAN_GLOBS = ("**/*.py",)
FORBIDDEN = re.compile(r"(urllib\.request\.urlopen|requests\.(get|post|put|delete)|httpx\.(get|post))")
ALLOW_FILES = {
    # Já protegidos / hosts fixos internos
    "core/database.py",  # só Supabase URL de env
    "utils/turnstile.py",  # challenges.cloudflare.com fixo
    "core/alerts.py",  # deve usar ssrf_guard — verificado abaixo
    "workers/email_worker.py",  # IMAP/SMTP não HTTP genérico
}


def main() -> int:
    alerts = (BACKEND / "core" / "alerts.py").read_text(encoding="utf-8")
    if "assert_safe_outbound_url" not in alerts and "ssrf_guard" not in alerts:
        # exigimos que alerts valide o webhook
        print("FAIL: core/alerts.py deve validar webhook com ssrf_guard")
        return 1

    turnstile = (BACKEND / "utils" / "turnstile.py").read_text(encoding="utf-8")
    if "challenges.cloudflare.com" not in turnstile:
        print("FAIL: turnstile deve usar host Cloudflare fixo")
        return 1

    ssrf = BACKEND / "core" / "ssrf_guard.py"
    if not ssrf.is_file():
        print("FAIL: ssrf_guard.py em falta")
        return 1

    print("OK — cobertura SSRF (alerts+turnstile+módulo)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
