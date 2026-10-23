"""Upload para Supabase Storage — path sanitizado; privado = só URL assinada."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from core.database import get_db

logger = logging.getLogger("diomika-api")

BUCKET = (
    os.getenv("SUPABASE_STORAGE_BUCKET")
    or os.getenv("VITE_SUPABASE_STORAGE_BUCKET")
    or "product-images"
)

_SAFE_PATH = re.compile(r"[^a-zA-Z0-9._/\-]")


def sanitize_storage_path(dest_path: str) -> str:
    cleaned = dest_path.replace("\\", "/").lstrip("/")
    cleaned = _SAFE_PATH.sub("_", cleaned)
    parts = [p for p in cleaned.split("/") if p and p not in (".", "..")]
    if not parts:
        raise ValueError("Caminho de storage inválido")
    return "/".join(parts)


def storage_backend() -> str:
    """Auto: R2 se credenciais existirem; senão Supabase (ambos free-tier possíveis)."""
    forced = (os.getenv("STORAGE_BACKEND") or "").strip().lower()
    if forced in ("r2", "supabase"):
        return forced
    if all(
        (os.getenv(k) or "").strip()
        for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")
    ):
        return "r2"
    return "supabase"


def storage_is_private() -> bool:
    if storage_backend() == "r2":
        # R2 público via R2_PUBLIC_BASE_URL ou signed
        return not bool((os.getenv("R2_PUBLIC_BASE_URL") or "").strip())
    return (os.getenv("SUPABASE_STORAGE_PRIVATE") or "").strip().lower() in ("1", "true", "yes")


def signed_url_ttl() -> int:
    return max(60, int(os.getenv("STORAGE_SIGNED_URL_TTL") or "3600"))


def get_public_url(storage_path: str) -> str:
    if storage_backend() == "r2":
        from utils.storage_r2 import resolve_url

        return resolve_url(storage_path)
    bucket = get_db().storage.from_(BUCKET)
    url = bucket.get_public_url(storage_path)
    if isinstance(url, dict):
        url = url.get("publicUrl", "")
    return str(url).replace("/object/public/public/", "/object/public/")


def get_signed_url(storage_path: str, expires_in: int | None = None) -> str:
    """URL assinada — falha fechada (nunca cai para pública se storage privado)."""
    if storage_backend() == "r2":
        from utils.storage_r2 import get_signed_url as r2_signed

        return r2_signed(storage_path, expires_in)
    ttl = expires_in if expires_in is not None else signed_url_ttl()
    bucket = get_db().storage.from_(BUCKET)
    res = bucket.create_signed_url(storage_path, ttl)
    if isinstance(res, dict):
        url = str(res.get("signedURL") or res.get("signedUrl") or "")
    else:
        url = str(res or "")
    if not url or not url.startswith("http"):
        raise RuntimeError("Falha ao gerar URL assinada do storage")
    return url


def resolve_delivery_url(storage_path: str) -> str:
    if storage_backend() == "r2":
        from utils.storage_r2 import resolve_url

        return resolve_url(storage_path)

    if storage_is_private():
        return get_signed_url(storage_path)
    return get_public_url(storage_path)


def upload_bytes(data: bytes, dest_path: str, content_type: str = "image/png", *, optimize: bool = True) -> str:
    """Envia bytes para o storage (Supabase ou R2) e devolve URL.

    `optimize=True` (omissão) redimensiona/recomprime fotos de catálogo no
    servidor — substitui a Image Transformation do Supabase (paga) por algo
    que funciona em qualquer plano. Códigos de barras devem passar
    `optimize=False`: precisam de ficar nítidos para serem lidos por um
    scanner, não comprimidos como uma fotografia.
    """
    from utils.image_validation import validate_upload_bytes

    dest_path = sanitize_storage_path(dest_path)
    max_bytes = int(os.getenv("STORAGE_MAX_UPLOAD_BYTES") or str(5 * 1024 * 1024))
    if len(data) > max_bytes:
        raise ValueError(f"Ficheiro demasiado grande (máx. {max_bytes} bytes)")

    validate_upload_bytes(data, dest_path)

    if optimize:
        from utils.image_resize import optimize_for_web

        data = optimize_for_web(data, dest_path)

    lower = dest_path.lower()
    if lower.endswith((".jpg", ".jpeg")):
        content_type = "image/jpeg"
    elif lower.endswith(".png"):
        content_type = "image/png"
    elif lower.endswith(".webp"):
        content_type = "image/webp"
    elif lower.endswith(".gif"):
        content_type = "image/gif"
    else:
        raise ValueError("Extensão de imagem não permitida")

    url = _put(data, dest_path, content_type)

    if optimize:
        from utils.image_resize import THUMB_WIDTHS, make_thumbnail, thumb_path

        for width in THUMB_WIDTHS:
            thumb = make_thumbnail(data, dest_path, width=width)
            if not thumb:
                break
            try:
                _put(thumb, thumb_path(dest_path, width), "image/webp")
            except Exception:
                # A loja cai no original se a miniatura faltar — não falhar o upload.
                logger.warning("miniatura w%s falhou para %s", width, dest_path, exc_info=True)

    return url


def _put(data: bytes, dest_path: str, content_type: str) -> str:
    if storage_backend() == "r2":
        from utils.storage_r2 import upload_bytes as r2_upload

        return r2_upload(data, dest_path, content_type)

    bucket = get_db().storage.from_(BUCKET)
    try:
        bucket.upload(
            dest_path,
            data,
            file_options={"content-type": content_type, "upsert": "true", "cache-control": "31536000"},
        )
    except TypeError:
        bucket.upload(dest_path, data)

    return resolve_delivery_url(dest_path)


def upload_file(local_path: str, dest_path: str, content_type: str = "image/png") -> str:
    path = Path(local_path)
    with path.open("rb") as f:
        return upload_bytes(f.read(), dest_path, content_type)
