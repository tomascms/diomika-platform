"""Ficheiros de actualização do backoffice de secretária (electron-updater, provider "generic").

Os instaladores levam embutido o segredo do gate desktop, por isso não ficam
num sítio público: servem-se daqui, debaixo de /system, que em produção só
responde a pedidos com o header do gate (PrivilegedPathMiddleware + WAF da
Cloudflare). Não exige login — a app verifica actualizações antes de alguém
entrar. Os ficheiros são publicados por deploy/publish_backoffice_update.py
para backend-api/data/desktop-updates (volume persistente na VM).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from core.local_only import admin_must_be_local
from paths import BACKEND_ROOT

UPDATES_DIR = Path(os.getenv("DESKTOP_UPDATES_DIR") or (BACKEND_ROOT / "data" / "desktop-updates"))
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,150}$")

router = APIRouter(
    prefix="/system/desktop-updates",
    tags=["Backoffice desktop"],
    dependencies=[Depends(admin_must_be_local)],
)


def _resolve(filename: str) -> Path:
    if not _NAME_RE.match(filename) or ".." in filename:
        raise HTTPException(status_code=404, detail="Não encontrado")
    base = UPDATES_DIR.resolve()
    path = (base / filename).resolve()
    if path.parent != base or not path.is_file():
        raise HTTPException(status_code=404, detail="Não encontrado")
    return path


@router.api_route("/{filename}", methods=["GET", "HEAD"])
def get_update_file(filename: str):
    path = _resolve(filename)
    is_manifest = path.suffix in (".yml", ".yaml")
    return FileResponse(
        path,
        media_type="text/yaml; charset=utf-8" if is_manifest else "application/octet-stream",
        headers={
            # O manifesto (latest.yml) tem de ser sempre o actual; os binários
            # têm a versão no nome, podem ficar em cache.
            "Cache-Control": "no-cache" if is_manifest else "private, max-age=86400",
            # Já comprimidos: impede o GZipMiddleware de recomprimir 80 MB na VM.
            "Content-Encoding": "identity",
        },
    )
