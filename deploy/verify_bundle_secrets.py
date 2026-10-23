#!/usr/bin/env python3
"""Verifica que o build da loja nao contem secrets server-side."""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "frontend-web" / "dist"

FORBIDDEN_PATTERNS = [
    (re.compile(r"service_role", re.I), "service_role JWT"),
    (re.compile(r"SUPABASE_KEY"), "SUPABASE_KEY (service role)"),
    (re.compile(r"API_SECRET_KEY"), "API_SECRET_KEY"),
    (re.compile(r"MAIL_PASSWORD"), "MAIL_PASSWORD"),
    (re.compile(r"TURNSTILE_SECRET"), "TURNSTILE_SECRET_KEY"),
    (re.compile(r"SUPABASE_DB_PASSWORD"), "SUPABASE_DB_PASSWORD"),
    (re.compile(r"IMAP_PASSWORD"), "IMAP password"),
]

ALLOWED_PUBLIC = {
    "VITE_SUPABASE_URL",
    "VITE_SUPABASE_ANON_KEY",
    "VITE_SUPABASE_STORAGE_BUCKET",
    "VITE_API_BASE_URL",
    "VITE_TURNSTILE_SITE_KEY",
    "VITE_POSTHOG_KEY",
    "VITE_POSTHOG_HOST",
}


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    dotenv = ROOT / ".env"
    if dotenv.is_file():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def scan_dist(dist: Path, env: dict[str, str]) -> list[str]:
    failures: list[str] = []
    if not dist.is_dir():
        return ["dist/ em falta — corre npm run build primeiro"]

    text_blobs: list[tuple[str, str]] = []
    for path in dist.rglob("*"):
        if path.is_file() and path.suffix in {".js", ".html", ".css", ".json", ".map"}:
            try:
                text_blobs.append((str(path.relative_to(dist)), path.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                continue

    combined = "\n".join(t for _, t in text_blobs)

    for pattern, label in FORBIDDEN_PATTERNS:
        if pattern.search(combined):
            failures.append(f"Pattern proibido no bundle: {label}")

    server_secrets = [
        ("API_SECRET_KEY", env.get("API_SECRET_KEY", "")),
        ("SUPABASE_KEY", env.get("SUPABASE_KEY", "")),
        ("MAIL_PASSWORD", env.get("MAIL_PASSWORD", "")),
        ("TURNSTILE_SECRET_KEY", env.get("TURNSTILE_SECRET_KEY", "")),
        ("SUPABASE_DB_PASSWORD", env.get("SUPABASE_DB_PASSWORD", "")),
    ]
    for name, value in server_secrets:
        if value and len(value) >= 8 and value in combined:
            failures.append(f"Valor literal de {name} encontrado no bundle")

    anon = env.get("VITE_SUPABASE_ANON_KEY", "")
    service = env.get("SUPABASE_KEY", "")
    if anon and service and anon == service:
        failures.append("VITE_SUPABASE_ANON_KEY = SUPABASE_KEY (service role exposto como anon!)")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=DIST)
    args = parser.parse_args()
    env = load_env()
    failures = scan_dist(args.dist, env)
    print("=== Verificacao bundle (F12) ===\n")
    if failures:
        for f in failures:
            print(f"  [FAIL] {f}")
        print(f"\n{len(failures)} problema(s) — NAO fazer deploy.")
        return 1
    print("  [OK] Nenhum secret server-side no bundle da loja")
    print("  [OK] Chaves publicas esperadas (anon, API URL, Turnstile site) podem aparecer — protegidas por RLS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
