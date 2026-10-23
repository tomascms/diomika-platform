"""Normalização de URLs e caminhos de imagem (Storage Supabase)."""
from __future__ import annotations

import os
import re
from pathlib import Path
from uuid import uuid4

from utils.storage import BUCKET, get_public_url, upload_file
from utils.image_validation import validate_image_path

LOCAL_PATH_PATTERN = re.compile(r"^[A-Za-z]:[/\\]|^[/\\]")


def is_http_url(value: str) -> bool:
    return bool(value) and str(value).strip().lower().startswith(("http://", "https://"))


def is_local_path(value: str) -> bool:
    if not value or is_http_url(value):
        return False
    normalized = str(value).strip().replace("\\", "/")
    if LOCAL_PATH_PATTERN.match(normalized):
        return True
    return Path(value).exists()


def content_type_for_path(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "image/png")


def normalize_storage_url(url: str) -> str:
    """Corrige URLs antigas sem o nome do bucket ou com segmentos duplicados."""
    if not url or not is_http_url(url):
        return url

    cleaned = url.strip().replace("/object/public/public/", "/object/public/")
    supabase_url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    marker = "/storage/v1/object/public/"
    if marker not in cleaned:
        return cleaned

    prefix, path = cleaned.split(marker, 1)
    path = path.lstrip("/")
    if not path or path.startswith(f"{BUCKET}/"):
        return cleaned

    # URLs antigas: /public/products/... ou /public/images/... (bucket em falta)
    return f"{prefix}{marker}{BUCKET}/{path}"


def resolve_image_value(value: str, table: str, field: str) -> str:
    """Mantém URL válida, faz upload de ficheiro local, ou normaliza URL legada."""
    if not value or not str(value).strip():
        return ""

    value = str(value).strip()
    if is_http_url(value):
        return normalize_storage_url(value)

    local_path = Path(value)
    if not local_path.exists():
        raise FileNotFoundError(f"Imagem não encontrada: {value}")

    validate_image_path(str(local_path))

    dest = f"{table}/{field}/{uuid4().hex}{local_path.suffix.lower()}"
    return upload_file(str(local_path), dest, content_type_for_path(str(local_path)))


def resolve_image_list(values: list[str], table: str, field: str) -> list[str]:
    resolved: list[str] = []
    missing: list[str] = []

    for raw in values:
        item = str(raw).strip()
        if not item:
            continue
        try:
            resolved.append(resolve_image_value(item, table, field))
        except FileNotFoundError:
            missing.append(item)

    if missing:
        raise FileNotFoundError(
            "Imagens em falta no disco (selecione ficheiros novamente):\n"
            + "\n".join(f"• {p}" for p in missing[:5])
            + (f"\n… e mais {len(missing) - 5}" if len(missing) > 5 else "")
        )

    return resolved
