"""Carrega variáveis de ambiente a partir de um único .env na raiz do projeto."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from paths import PROJECT_ROOT
from core.database_url import get_database_url

ENV_FILE = PROJECT_ROOT / ".env"


def _ensure_ssl_certs() -> None:
    """Windows/Python 3.14 — certificados CA para Supabase httpx."""
    try:
        import certifi

        bundle = certifi.where()
        os.environ.setdefault("SSL_CERT_FILE", bundle)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", bundle)
    except ImportError:
        pass


def load_project_env() -> Path:
    """Carrega .env da raiz — valores do ficheiro têm prioridade (setup local)."""
    _ensure_ssl_certs()
    load_dotenv(ENV_FILE, override=False)
    db_url = get_database_url()
    if db_url and not (os.getenv("DATABASE_URL") or "").strip():
        os.environ["DATABASE_URL"] = db_url
    return ENV_FILE
