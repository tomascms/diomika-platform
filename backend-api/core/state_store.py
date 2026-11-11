"""Documentos JSON pequenos e duráveis (contas do backoffice, estado do worker de email).

Por omissão num ficheiro em `data/`. Com STATE_STORE=supabase ficam na tabela `app_state`: no Render grátis o
disco apaga-se a cada arranque (db/migrations/2026-11-03_app_state.sql).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from paths import BACKEND_ROOT

DATA_DIR = BACKEND_ROOT / "data"


def _supabase() -> bool:
    return (os.getenv("STATE_STORE") or "").strip().lower() == "supabase"


def load(name: str, default: Any) -> Any:
    if _supabase():
        from core.database import get_db

        rows = get_db().table("app_state").select("value").eq("key", name).limit(1).execute().data
        return rows[0]["value"] if rows else default
    path = DATA_DIR / f"{name}.json"
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save(name: str, value: Any) -> None:
    if _supabase():
        from core.database import get_db

        get_db().table("app_state").upsert(
            {"key": name, "value": value, "updated_at": datetime.now(timezone.utc).isoformat()}
        ).execute()
        return
    path = DATA_DIR / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
