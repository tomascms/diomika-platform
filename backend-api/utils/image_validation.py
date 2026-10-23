"""Validação de imagens no upload — magic bytes + rejeição de polyglots/arquivos compostos."""
from __future__ import annotations

from pathlib import Path

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

_MAGIC = {
    b"\xff\xd8\xff": {".jpg", ".jpeg"},
    b"\x89PNG\r\n\x1a\n": {".png"},
    b"GIF87a": {".gif"},
    b"GIF89a": {".gif"},
    b"RIFF": {".webp"},
}

# Assinaturas que nunca devem aparecer em imagem de catálogo
_FORBIDDEN_EMBEDDED = (
    b"PK\x03\x04",  # ZIP
    b"%PDF",
    b"<!DOCTYPE",
    b"<html",
    b"<svg",
    b"<?php",
    b"#!/",
)


def validate_image_path(path: str) -> None:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Imagem não encontrada: {path}")
    if p.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Formato não permitido: {p.suffix}. Use JPG, PNG ou WebP.")
    size = p.stat().st_size
    if size > MAX_IMAGE_BYTES:
        raise ValueError(f"Imagem demasiado grande ({size // 1024} KB). Máximo: {MAX_IMAGE_BYTES // 1024} KB.")
    validate_upload_bytes(p.read_bytes(), p.name)


def validate_upload_bytes(data: bytes, filename: str) -> None:
    if not data:
        raise ValueError("Ficheiro vazio.")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"Imagem demasiado grande. Máximo: {MAX_IMAGE_BYTES // 1024} KB.")

    ext = Path(filename or "").suffix.lower() or ".png"
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Formato não permitido: {ext}. Use JPG, PNG, WebP ou GIF.")

    head = data[:12]
    matched = False
    for magic, exts in _MAGIC.items():
        if head.startswith(magic):
            if ext in exts or (
                magic == b"RIFF" and ext == ".webp" and len(data) > 12 and data[8:12] == b"WEBP"
            ):
                matched = True
                break
    if not matched:
        raise ValueError("Conteúdo do ficheiro não corresponde a uma imagem válida.")

    # Polyglot / zip bomb / HTML-as-image: procurar assinaturas perigosas após o header
    scan = data[16 : min(len(data), 64 * 1024)].lower()
    for needle in _FORBIDDEN_EMBEDDED:
        if needle.lower() in scan:
            raise ValueError("Ficheiro rejeitado: conteúdo embutido não permitido.")
