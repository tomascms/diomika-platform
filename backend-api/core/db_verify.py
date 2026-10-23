"""Verificação Supabase — REST (PostgREST) ou PostgreSQL directo."""
from __future__ import annotations

from psycopg2 import sql


def check_via_rest() -> tuple[bool, str]:
    try:
        from core.database import get_db

        get_db().table("categories").select("id").limit(1).execute()
        return True, "ok (REST)"
    except Exception as exc:
        return False, str(exc)[:120]


def check_tables_via_postgres(tables: list[str]) -> tuple[bool, str, list[str]]:
    from core.database_url import iter_database_urls

    urls = list(iter_database_urls())
    if not urls:
        return False, "sem DATABASE_URL / SUPABASE_DB_PASSWORD", []

    url = urls[0]
    if "sslmode=" not in url:
        url += "?sslmode=require" if "?" not in url else "&sslmode=require"

    import psycopg2

    missing: list[str] = []
    try:
        conn = psycopg2.connect(url, connect_timeout=15)
        conn.autocommit = True
        with conn.cursor() as cur:
            for table in tables:
                try:
                    cur.execute(
                        sql.SQL("SELECT 1 FROM {} LIMIT 1").format(sql.Identifier(table))
                    )
                except Exception:
                    missing.append(table)
        conn.close()
    except Exception as exc:
        return False, str(exc)[:120], missing

    if missing:
        return True, f"PostgreSQL ok — em falta: {', '.join(missing)}", missing
    return True, "ok (PostgreSQL)", []


def verify_supabase(*, infra_tables: list[str]) -> dict:
    """Devolve estado consolidado para deploy/check.py."""
    rest_ok, rest_msg = check_via_rest()
    pg_ok, pg_msg, missing = check_tables_via_postgres(["categories", *infra_tables])
    return {
        "rest_ok": rest_ok,
        "rest_msg": rest_msg,
        "pg_ok": pg_ok,
        "pg_msg": pg_msg,
        "missing_tables": missing,
    }
