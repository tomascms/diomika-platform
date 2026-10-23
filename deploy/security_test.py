#!/usr/bin/env python3
"""
Testes de segurança HTTP — API em execução.

Uso:
  python deploy/security_test.py
  python deploy/security_test.py --url https://api.diomika.com
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import certifi
except ImportError:
    certifi = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend-api"))
sys.path.insert(0, str(ROOT / "deploy"))

from core.env_loader import load_project_env
from test_http import load_test_env, ssl_context

load_project_env()
load_test_env()

FAILURES: list[str] = []


def header_value(headers: dict[str, str], name: str) -> str | None:
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return None


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "OK" if ok else "FAIL"
    line = f"  [{status}] {name}" + (f" — {detail}" if detail else "")
    print(line)
    if not ok:
        FAILURES.append(name)


def request(
    method: str,
    url: str,
    *,
    headers: dict | None = None,
    body: dict | None = None,
    timeout: float = 12.0,
) -> tuple[int | None, dict[str, str], str, bool]:
    data = None
    req_headers = dict(headers or {})
    # Cloudflare / WAF rejeitam User-Agent vazio (Python urllib default)
    req_headers.setdefault("User-Agent", "DiomikaSecurityTest/1.0")
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    ctx = ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            text = resp.read(4096).decode("utf-8", errors="replace")
            return resp.status, dict(resp.headers), text, False
    except urllib.error.HTTPError as exc:
        text = exc.read(4096).decode("utf-8", errors="replace")
        return exc.code, dict(exc.headers), text, False
    except Exception as exc:
        return None, {}, str(exc), True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"))
    args = parser.parse_args()
    base = args.url.rstrip("/")
    api_key = os.getenv("API_SECRET_KEY", "")

    print("=== Diomika — security test ===\n")
    print(f"Alvo: {base}\n")

    status, headers, body, err = request("GET", f"{base}/health")
    if err:
        print(f"  API inacessível em {base} — arranca a API ou define --url")
        return 2
    check("GET /health", status == 200, f"status={status}")
    check("Header X-Content-Type-Options", header_value(headers, "X-Content-Type-Options") == "nosniff")
    check("Header X-Frame-Options", header_value(headers, "X-Frame-Options") in ("DENY", "SAMEORIGIN"))
    check("Header X-Request-Id", bool(header_value(headers, "X-Request-Id")))

    status, headers, body, _ = request("GET", f"{base}/")
    check("GET /", status == 200 and "diomika-api" in body, f"status={status}")

    status, _, body, _ = request("GET", f"{base}/robots.txt")
    check("GET /robots.txt", status == 200 and "Disallow: /" in body, f"status={status}")

    status, _, body, _ = request("GET", f"{base}/.well-known/security.txt")
    check("GET /.well-known/security.txt", status == 200 and "Contact:" in body, f"status={status}")

    # /system e /admin: na edge pública o WAF pode devolver 403 HTML (preferível).
    # Em localhost a API responde 401/200 conforme chave.
    public_edge = base.startswith("https://")
    status, _, _, _ = request("GET", f"{base}/system/workspace")
    if api_key:
        check("GET /system/workspace sem chave bloqueado", status in (401, 403, 503), f"status={status}")
        status, _, _, _ = request(
            "GET",
            f"{base}/system/workspace",
            headers={"X-API-Key": "invalid-key-00000000"},
        )
        check(
            "GET /system/workspace chave inválida",
            status in (401, 403) if public_edge else status == 401,
            f"status={status}",
        )
        status, _, _, _ = request(
            "GET",
            f"{base}/system/workspace",
            headers={"X-API-Key": api_key},
        )
        check(
            "GET /system/workspace chave válida",
            status in (200, 403) if public_edge else status == 200,
            f"status={status}" + (" (WAF edge)" if status == 403 and public_edge else ""),
        )
    else:
        check("GET /system/workspace (dev sem API_SECRET_KEY)", status == 200, f"status={status}")

    status, _, body, _ = request(
        "POST",
        f"{base}/contacto",
        body={
            "nome": "Teste Seguranca",
            "email": "test@example.com",
            "contacto": "912345678",
            "assunto": "Teste",
            "mensagem": "Mensagem de teste de seguranca com comprimento minimo.",
            "website": "http://spam.bot",
        },
    )
    check("POST /contacto honeypot bloqueado", status == 400, f"status={status}")

    status, _, _, _ = request(
        "POST",
        f"{base}/orcamentos",
        body={"nome": "x", "email": "not-an-email", "linhas": []},
    )
    check("POST /orcamentos email inválido", status in (400, 422), f"status={status}")

    for path in ("/openapi.json", "/api/docs", "/api/redoc"):
        status, _, _, _ = request("GET", f"{base}{path}")
        check(f"GET {path} desactivado", status in (404, 403), f"status={status}")

    status, _, _, _ = request("GET", f"{base}/admin/crud/categories")
    check("GET /admin/crud/categories sem chave", status in (401, 403), f"status={status}")

    status, _, _, _ = request("GET", f"{base}/contacto")
    check("GET /contacto sem chave", status in (401, 403), f"status={status}")

    status, _, _, _ = request("GET", f"{base}/health/detail")
    check("GET /health/detail sem chave", status in (401, 403), f"status={status}")

    status, _, body, _ = request("GET", f"{base}/orcamentos/00000000-0000-0000-0000-000000000000/pdf")
    check("GET orcamento PDF sem chave", status in (401, 403, 404), f"status={status}")
    if body and any(x in body.lower() for x in ("traceback", "postgresql", "supabase")):
        check("Resposta sem stack trace", False, "leak detectado")

    print()
    if FAILURES:
        print(f"Falharam {len(FAILURES)} testes: {', '.join(FAILURES)}")
        return 1
    print("OK — testes de segurança passaram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
