#!/usr/bin/env python3
"""Fase 3 — Smoke tests API + frontend publico."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deploy"))
sys.path.insert(0, str(ROOT / "backend-api"))

from launch_lib import DOMAIN, Report, http_get, save_launch_state  # noqa: E402
from test_http import load_test_env  # noqa: E402

load_test_env()


def smoke(*, api_url: str, site_url: str | None = None) -> Report:
    report = Report()
    api = api_url.rstrip("/")
    print(f"\n=== SMOKE API {api} ===\n")

    st, body, ms = http_get(f"{api}/health")
    report.add("GET /health", st == 200 and "online" in body, f"{st} {ms:.0f}ms")

    st, body, ms = http_get(f"{api}/health/ready")
    report.add("GET /health/ready", st == 200, f"{st} {ms:.0f}ms")

    st, body, ms = http_get(f"{api}/categorias")
    report.add("GET /categorias", st == 200, f"{st} {ms:.0f}ms")

    st, body, ms = http_get(f"{api}/catalogo/meta")
    report.add("GET /catalogo/meta", st == 200, f"{st} {ms:.0f}ms")

    # Rotas sensiveis NAO devem abrir sem auth
    for path in ("/admin/crud/categories", "/system/workspace", "/contacto", "/health/detail"):
        st, _, ms = http_get(f"{api}{path}")
        blocked = st in (401, 403, 404, 405)
        report.add(f"block {path}", blocked, f"status={st}")

    # Docs off em producao
    st, _, _ = http_get(f"{api}/openapi.json")
    report.add("openapi hidden", st in (404, 401, 403), f"status={st}", critical=False)

    if site_url:
        site = site_url.rstrip("/")
        print(f"\n=== SMOKE SITE {site} ===\n")
        st, body, ms = http_get(site)
        report.add("GET / (loja)", st == 200 and ("html" in body.lower() or "<!doctype" in body.lower() or "Diomika" in body), f"{st} {ms:.0f}ms")
        # Manutenção não deve estar activa no smoke pós-ativação
        if "Estamos a actualizar" in body:
            report.add("site not maintenance", False, "pagina de manutencao activa")
        else:
            report.add("site not maintenance", True)

    save_launch_state({"smoke_ok": report.ok, "smoke_api": api, "failed_smoke": report.failed()})
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=os.getenv("API_BASE_URL") or f"https://api.{DOMAIN}")
    parser.add_argument("--site", default="")
    args = parser.parse_args()
    os.environ.setdefault("DEPLOY_TLS_INSECURE", "1")
    report = smoke(api_url=args.api, site_url=args.site or None)
    print()
    if report.ok:
        print("SMOKE OK")
        return 0
    print("SMOKE FALHOU:", ", ".join(report.failed()))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
