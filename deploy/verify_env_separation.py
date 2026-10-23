#!/usr/bin/env python3
"""Regras de separação beta vs produção final."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "backend-api" / "core" / "config.py"


def main() -> int:
    text = CONFIG.read_text(encoding="utf-8")
    admin_users = (ROOT / "backend-api" / "core" / "admin_users.py").read_text(encoding="utf-8")
    required_config = [
        "REDIS_URL",
        "SUPABASE_STORAGE_PRIVATE",
        "ADMIN_ALLOW_REMOTE",
        "DIOMIKA_SSL_INSECURE",
        "is_beta",
        "CORS_ORIGINS",
        "ALLOWED_HOSTS",
    ]
    missing = [r for r in required_config if r not in text]
    if missing:
        print("FAIL config.py sem:", ", ".join(missing))
        return 1
    if "ADMIN_MFA_REQUIRED" not in admin_users:
        print("FAIL admin_users.py sem ADMIN_MFA_REQUIRED")
        return 1
    # Produção final não pode ter escape remoto
    local_only = (ROOT / "backend-api" / "core" / "local_only.py").read_text(encoding="utf-8")
    if 'os.getenv("ADMIN_ALLOW_REMOTE")' in local_only:
        print("FAIL: ADMIN_ALLOW_REMOTE ainda lido em local_only")
        return 1
    print("OK — regras beta/prod separadas no código")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
