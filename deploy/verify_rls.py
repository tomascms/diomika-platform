#!/usr/bin/env python3
"""Verifica que a chave anon Supabase nao le tabelas sensiveis."""
from __future__ import annotations

import argparse
import os
import ssl
import sys
from pathlib import Path

import httpx
import certifi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend-api"))

from core.env_loader import load_project_env

load_project_env()

SENSITIVE_TABLES = [
    "pedidos_orcamento",
    "encomendas_internas",
    "contact_messages",
    "message_history",
    "outbox_events",
    "saga_instances",
    "idempotency_keys",
    "admin_audit_log",
]

_ssl = ssl.create_default_context(cafile=certifi.where())
# So CLI: DEPLOY_TLS_INSECURE — nunca DIOMIKA_SSL_INSECURE (afecta a API)
if (os.getenv("DEPLOY_TLS_INSECURE") or "").strip().lower() in ("1", "true", "yes"):
    _ssl.check_hostname = False
    _ssl.verify_mode = ssl.CERT_NONE
_client = httpx.Client(verify=_ssl, timeout=12.0)


def supabase_get(table: str, url: str, anon_key: str) -> tuple[int, str]:
    resp = _client.get(
        f"{url.rstrip('/')}/rest/v1/{table}?select=*&limit=1",
        headers={"apikey": anon_key, "Authorization": f"Bearer {anon_key}"},
    )
    return resp.status_code, resp.text[:512]


def main() -> int:
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    url = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL") or ""
    anon = os.getenv("VITE_SUPABASE_ANON_KEY") or ""
    if not url or not anon:
        print("ERRO: VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY em falta")
        return 2

    print("=== Verificacao RLS Supabase (chave anon) ===\n")
    failures: list[str] = []
    for table in SENSITIVE_TABLES:
        status, body = supabase_get(table, url, anon)
        if status == 200:
            import json

            try:
                data = json.loads(body) if body.strip().startswith("[") else []
            except json.JSONDecodeError:
                data = None
            if data:
                failures.append(f"{table}: anon leu {len(data)} registo(s)!")
            else:
                print(f"  [OK] {table}: vazio ou bloqueado (200 sem dados)")
        elif status in (401, 403, 404, 406):
            print(f"  [OK] {table}: bloqueado (HTTP {status})")
        else:
            print(f"  [?] {table}: HTTP {status}")

    if failures:
        for f in failures:
            print(f"  [FAIL] {f}")
        return 1
    print("\nOK — tabelas sensiveis nao expostas via chave anon.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
