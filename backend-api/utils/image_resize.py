"""Redimensiona/comprime imagens de catálogo no upload (servidor) — sem
depender do Supabase Image Transformation (feature paga, Plano Pro+).

O projecto corre em infraestrutura de custo zero (ver deploy/docker-compose.free.yml),
por isso a optimização tem de acontecer uma vez, no upload, e não por-pedido
numa API de transformação. Gifs animados e imagens já pequenas ficam
intocados; PNG/JPEG/WebP grandes são redimensionados e recomprimidos.
"""
from __future__ import annotations

import io
from pathlib import Path

MAX_DIMENSION = 1600  # suficiente para a maior imagem usada na loja (hero/detalhe)
JPEG_QUALITY = 82
WEBP_QUALITY = 82
PNG_COMPRESS_LEVEL = 9


def optimize_for_web(data: bytes, filename: str, *, max_dimension: int = MAX_DIMENSION) -> bytes:
    """Redimensiona (se maior que max_dimension) e recomprime. Nunca falha
    "a mais" — se o Pillow não conseguir processar, devolve os bytes originais."""
    ext = Path(filename or "").suffix.lower()
    if ext == ".gif":
        return data  # animações — não mexer

    try:
        from PIL import Image, ImageOps
    except ImportError:
        return data

    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)  # corrige rotação de fotos de telemóvel

        if max(img.width, img.height) > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

        out = io.BytesIO()
        if ext in (".jpg", ".jpeg"):
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        elif ext == ".webp":
            img.save(out, format="WEBP", quality=WEBP_QUALITY, method=6)
        elif ext == ".png":
            img.save(out, format="PNG", optimize=True, compress_level=PNG_COMPRESS_LEVEL)
        else:
            return data

        optimized = out.getvalue()
        # Só usa o resultado se for mesmo mais pequeno — nunca piorar.
        return optimized if len(optimized) < len(data) else data
    except Exception:
        return data


THUMB_WIDTH = 480  # cartões e listas da loja (até ~240 px CSS em ecrãs 2x)
THUMB_SUFFIX = f".w{THUMB_WIDTH}.webp"
# 480 para listas; 960 para imagens grandes (hero, detalhe) em telemóveis com ecrã 2-3x.
THUMB_WIDTHS = (THUMB_WIDTH, 960)


def thumb_path(storage_path: str, width: int = THUMB_WIDTH) -> str:
    """`a/b.jpg` → `a/b.jpg.w480.webp` (o original recupera-se tirando o sufixo)."""
    return f"{storage_path}.w{width}.webp"


def is_thumb(storage_path: str) -> bool:
    return any(storage_path.endswith(f".w{w}.webp") for w in THUMB_WIDTHS)


def make_thumbnail(data: bytes, filename: str, *, width: int = THUMB_WIDTH) -> bytes | None:
    """Miniatura WebP para listas. None se não for uma imagem estática processável."""
    if Path(filename or "").suffix.lower() == ".gif":
        return None
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return None
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        if img.width > width:
            img.thumbnail((width, width * 4), Image.LANCZOS)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
        out = io.BytesIO()
        img.save(out, format="WEBP", quality=75, method=6)
        return out.getvalue()
    except Exception:
        return None
