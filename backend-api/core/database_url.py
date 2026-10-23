"""URL PostgreSQL — directa, pooler ou DATABASE_URL explícita."""
from __future__ import annotations

import os
import re
from urllib.parse import quote_plus

POOLER_REGIONS = (
    "eu-west-1",
    "eu-west-2",
    "eu-central-1",
    "us-east-1",
    "us-west-1",
    "ap-southeast-1",
)


def _supabase_project_ref() -> str | None:
    url = (os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL") or "").strip()
    match = re.search(r"https://([^.]+)\.supabase\.co", url)
    return match.group(1) if match else None


def iter_database_urls() -> list[str]:
    """Lista de URLs a tentar (ordem de preferência)."""
    explicit = (os.getenv("DATABASE_URL") or "").strip()
    if explicit:
        return [explicit]

    password = (os.getenv("SUPABASE_DB_PASSWORD") or "").strip()
    if not password:
        return []

    ref = _supabase_project_ref()
    if not ref:
        return []

    enc = quote_plus(password)
    urls: list[str] = []

    host = (os.getenv("SUPABASE_DB_HOST") or "").strip()
    port = (os.getenv("SUPABASE_DB_PORT") or "5432").strip()
    user = (os.getenv("SUPABASE_DB_USER") or "postgres").strip()

    if host:
        urls.append(f"postgresql://{user}:{enc}@{host}:{port}/postgres")
        return urls

    urls.append(f"postgresql://postgres:{enc}@db.{ref}.supabase.co:5432/postgres")

    for region in POOLER_REGIONS:
        pooler = f"aws-0-{region}.pooler.supabase.com"
        urls.append(f"postgresql://postgres.{ref}:{enc}@{pooler}:5432/postgres")
        urls.append(f"postgresql://postgres.{ref}:{enc}@{pooler}:6543/postgres")

    return urls


def get_database_url() -> str | None:
    urls = iter_database_urls()
    return urls[0] if urls else None
