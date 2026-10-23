#!/usr/bin/env python3
"""
Verificação pré-deploy. Uso:
  python deploy/check.py --codebase --build   # pronto para deploy (sem URLs prod)
  python deploy/check.py --production         # no dia do deploy (URLs https)
  python deploy/check.py --build              # local + build
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend-api"))

from core.env_loader import load_project_env
from core.database_url import get_database_url

load_project_env()
OK, WARN, ERR = "OK", "!", "X"
passed: list[str] = []
warnings: list[str] = []
errors: list[str] = []


def check(name: str, ok: bool, msg: str, *, critical: bool = True) -> None:
    line = f"{OK if ok else (ERR if critical else WARN)} {name}: {msg}"
    (passed if ok else errors if critical else warnings).append(line)


def check_files() -> None:
    required = [
        "Dockerfile",
        "requirements.txt",
        ".dockerignore",
        "README.md",
        "docs/runbook.md",
        "docs/guia-cliente.md",
        "deploy/create_gcp_vm.py",
        "deploy/docker-compose.free.yml",
        "deploy/env.free.example",
        "deploy/security_gate.py",
        "deploy/verify_csp.py",
        "deploy/uptime_check.py",
        "deploy/verify_production.py",
        "deploy/smoke_test.py",
        "deploy/start_local_api.py",
        "db/legacy/supabase_pre_deploy.sql",
        "backoffice-desktop/electron/main.cjs",
        "backoffice-desktop/electron/api-origin.cjs",
        "db/legacy/production_setup.sql",
        "db/migrations/2026-10-01_0001_unified_catalog_schema.sql",
        "db/migrations/2026-10-01_0002_migrate_catalog_data.sql",
        "db/RUNBOOK_unified_catalog_migration.md",
    ]
    for rel in required:
        check(f"Ficheiro {rel}", (ROOT / rel).is_file(), "ok" if (ROOT / rel).is_file() else "em falta")


def check_gitignore() -> None:
    gi = ROOT / ".gitignore"
    if not gi.is_file():
        check(".gitignore", False, "em falta")
        return
    text = gi.read_text(encoding="utf-8")
    check(".gitignore .env.local", ".env.local" in text, "protege cópias locais")


def check_env(production: bool, codebase_only: bool = False) -> None:
    env = (os.getenv("DIOMIKA_ENV") or "development").lower()
    strict = production and not codebase_only

    if strict:
        check("DIOMIKA_ENV", env == "production", env, critical=False)
        if env != "production":
            warnings.append(f"{WARN} DIOMIKA_ENV: development — definir production na VM/Pages")

    for var in ("SUPABASE_URL", "SUPABASE_KEY", "API_SECRET_KEY"):
        check(var, bool(os.getenv(var)), "definido" if os.getenv(var) else "em falta", critical=strict)

    notify = os.getenv("CONTACT_NOTIFY_EMAIL") or os.getenv("MAIL_FROM")
    check(
        "CONTACT_NOTIFY_EMAIL",
        bool(notify),
        notify or "recomendado para alertas de contacto",
        critical=False,
    )

    db = get_database_url()
    sql_hint = "db/legacy/supabase_pre_deploy.sql no SQL Editor"
    check(
        "SUPABASE_DB_PASSWORD",
        bool(db),
        "configurado" if db else f"em falta — usar {sql_hint}",
        critical=False,
    )

    cors = os.getenv("CORS_ORIGINS", "")
    if strict:
        ok_cors = bool(cors) and "localhost" not in cors and "127.0.0.1" not in cors
        check("CORS_ORIGINS", ok_cors, cors or "definir URL da loja (pages.dev)", critical=True)
    else:
        msg = cors or ("localhost OK (dev)" if codebase_only else "não definido")
        check("CORS_ORIGINS", bool(cors) or codebase_only, msg, critical=False)

    vite_api = os.getenv("VITE_API_BASE_URL", "")
    if strict:
        ok_vite = bool(vite_api) and vite_api.startswith("https://")
        check("VITE_API_BASE_URL", ok_vite, vite_api or "https://api.diomika.com", critical=True)
    else:
        msg = vite_api or ("localhost OK (dev)" if codebase_only else "não definido")
        check("VITE_API_BASE_URL", bool(vite_api) or codebase_only, msg, critical=False)

    anon = os.getenv("VITE_SUPABASE_ANON_KEY", "")
    service = os.getenv("SUPABASE_KEY", "")
    if anon and service and anon == service:
        check("Supabase keys", False, "anon key = service key — perigo!", critical=True)
    elif strict:
        check("VITE_SUPABASE_ANON_KEY", bool(anon), "definido" if anon else "em falta", critical=True)
    else:
        check("VITE_SUPABASE_ANON_KEY", bool(anon), "definido" if anon else "em falta", critical=False)

    embedded = (os.getenv("RUN_EMBEDDED_WORKERS") or "").lower()
    if strict:
        check(
            "RUN_EMBEDDED_WORKERS",
            embedded in ("1", "true", "yes", "") or env == "production",
            embedded or "true na VM (default em production)",
            critical=False,
        )

    mail_ok = all(os.getenv(k) for k in ("MAIL_SERVER", "MAIL_USERNAME", "MAIL_PASSWORD"))
    turnstile = (os.getenv("TURNSTILE_SECRET_KEY") or "").strip()
    if strict:
        check(
            "TURNSTILE_SECRET_KEY",
            bool(turnstile),
            "recomendado anti-spam contacto" if not turnstile else "ok",
            critical=False,
        )
    check("Email SMTP", mail_ok, "ok" if mail_ok else "incompleto", critical=strict)

    imap_ok = all(os.getenv(k) for k in ("IMAP_SERVER", "MAIL_USERNAME", "MAIL_PASSWORD"))
    check("Email IMAP", imap_ok, "ok" if imap_ok else "incompleto", critical=False)

    if strict:
        hosts = (os.getenv("ALLOWED_HOSTS") or "").strip()
        check("ALLOWED_HOSTS", bool(hosts), hosts or "api.diomika.com", critical=True)
        api_url = (os.getenv("API_BASE_URL") or "").strip()
        check("API_BASE_URL https", api_url.startswith("https://"), api_url or "em falta", critical=True)
        from core.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()
        if settings._turnstile_is_test_key():
            check("Turnstile producao", False, "chaves de teste — usa chaves reais Cloudflare Turnstile", critical=True)
        else:
            check("Turnstile producao", bool(turnstile), "chaves reais", critical=True)
        get_settings.cache_clear()


def check_supabase() -> None:
    from core.db_verify import verify_supabase

    infra = ["outbox_events", "saga_instances", "idempotency_keys"]
    state = verify_supabase(infra_tables=infra)

    if state["rest_ok"]:
        check("Supabase ligação", True, state["rest_msg"])
    elif state["pg_ok"] and not state["missing_tables"]:
        check("Supabase ligação", True, f"{state['pg_msg']} (REST indisponível neste PC)")
    elif state["pg_ok"]:
        check("Supabase ligação", True, state["pg_msg"], critical=False)
    else:
        check("Supabase ligação", False, state["rest_msg"] or state["pg_msg"])

    if state["rest_ok"]:
        table_pk = {
            "outbox_events": "id",
            "saga_instances": "id",
            "idempotency_keys": "key",
        }
        from core.database import get_db

        db_client = get_db()
        for table, pk in table_pk.items():
            try:
                db_client.table(table).select(pk).limit(1).execute()
                check(f"Tabela {table}", True, "ok")
            except Exception:
                check(
                    f"Tabela {table}",
                    False,
                    "aplicar SQL: db/legacy/supabase_pre_deploy.sql",
                    critical=False,
                )
        return

    if state["pg_ok"]:
        for table in infra:
            if table in state["missing_tables"]:
                check(
                    f"Tabela {table}",
                    False,
                    "aplicar SQL: db/legacy/supabase_pre_deploy.sql",
                    critical=False,
                )
            else:
                check(f"Tabela {table}", True, "ok (PostgreSQL)")
        check("Tabela categories", "categories" not in state["missing_tables"], "ok (PostgreSQL)" if "categories" not in state["missing_tables"] else "em falta")


def check_api_health() -> None:
    try:
        import urllib.request

        api = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        with urllib.request.urlopen(f"{api}/health", timeout=5) as resp:
            resp.read()
        check("API /health", True, api, critical=False)
    except Exception:
        check("API /health", False, "offline (opcional agora)", critical=False)


def check_frontend_build() -> None:
    fe = ROOT / "frontend-web"
    if not (fe / "package.json").is_file():
        check("Frontend build", False, "package.json em falta")
        return

    env = {
        **os.environ,
        "VITE_API_BASE_URL": os.getenv("VITE_API_BASE_URL") or "https://api.diomika.com",
        "VITE_SUPABASE_URL": os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL") or "https://example.supabase.co",
        "VITE_SUPABASE_ANON_KEY": os.getenv("VITE_SUPABASE_ANON_KEY") or "build-placeholder",
        "VITE_SUPABASE_STORAGE_BUCKET": os.getenv("VITE_SUPABASE_STORAGE_BUCKET") or "product-images",
    }
    print("\n--- A testar npm run build (pode demorar 1–2 min) ---\n")
    try:
        if not (fe / "node_modules").is_dir():
            subprocess.run(["npm", "ci"], cwd=fe, check=True, shell=os.name == "nt")
        subprocess.run(["npm", "run", "build"], cwd=fe, check=True, env=env, shell=os.name == "nt")
        dist = fe / "dist" / "index.html"
        check("Frontend build", dist.is_file(), str(dist) if dist.is_file() else "dist em falta")
    except subprocess.CalledProcessError as exc:
        check("Frontend build", False, f"falhou (exit {exc.returncode})")
    except FileNotFoundError:
        check("Frontend build", False, "npm não encontrado", critical=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificação pré-deploy Diomika")
    parser.add_argument("--production", action="store_true", help="Validar URLs de produção (dia do deploy)")
    parser.add_argument("--codebase", action="store_true", help="Código pronto — ignora localhost nos URLs")
    parser.add_argument("--beta", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--build", action="store_true", help="Testar build do frontend")
    args = parser.parse_args()

    if sum(bool(x) for x in (args.codebase, args.production, args.beta)) > 1:
        print("Use apenas um de: --codebase, --production, --beta.\n")
        return 1

    if args.beta:
        print("--beta removido; usa: python deploy/smoke_test.py --api https://api.diomika.com --site https://www.diomika.com\n")
        return 1

    if args.codebase:
        mode = "codebase (pré-deploy)"
    elif args.production:
        mode = "produção"
    else:
        mode = "local"
    print(f"\n=== Diomika — verificação pré-deploy ({mode}) ===\n")

    check_files()
    check_gitignore()
    check_env(args.production, codebase_only=args.codebase)
    # --codebase / CI: não exige rede real (SUPABASE_URL de exemplo falha DNS)
    if args.codebase:
        check(
            "Supabase ligação",
            True,
            "omitido em --codebase (validar com --production ou local com .env)",
            critical=False,
        )
    else:
        check_supabase()
    check_api_health()
    if args.build:
        check_frontend_build()

    for line in passed:
        print(line)
    for line in warnings:
        print(line)
    for line in errors:
        print(line)

    print(f"\n{len(passed)} ok | {len(warnings)} avisos | {len(errors)} erros\n")

    if errors:
        print("Corrija os erros antes do deploy.\n")
        return 1

    if args.codebase:
        print("Codebase OK. Deploy API: Actions → Deploy API (ou docs/runbook.md secção 2) | Loja: docs/runbook.md secção 1\n")
    elif args.production:
        print("Produção OK.\n")
    else:
        print("Local OK. Produção: python deploy/check.py --codebase\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
