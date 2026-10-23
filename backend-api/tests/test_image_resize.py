"""Optimização de imagens no upload — substitui a Image Transformation paga
do Supabase (o projecto corre em infraestrutura de custo zero)."""
from __future__ import annotations

import io

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from utils.image_resize import optimize_for_web  # noqa: E402


def _make_jpeg(width: int, height: int, quality: int = 95) -> bytes:
    img = Image.new("RGB", (width, height), color=(120, 60, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def test_large_jpeg_is_downscaled_and_shrunk():
    data = _make_jpeg(3000, 2000)
    out = optimize_for_web(data, "foto.jpg")
    assert len(out) < len(data)
    img = Image.open(io.BytesIO(out))
    assert max(img.size) <= 1600


def test_small_jpeg_is_not_upscaled():
    data = _make_jpeg(400, 300)
    out = optimize_for_web(data, "foto.jpg")
    img = Image.open(io.BytesIO(out))
    assert img.size == (400, 300)


def test_gif_is_left_untouched():
    img = Image.new("RGB", (2000, 2000), color=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="GIF")
    data = buf.getvalue()
    out = optimize_for_web(data, "anim.gif")
    assert out == data


def test_png_with_transparency_keeps_alpha():
    img = Image.new("RGBA", (2000, 1200), color=(10, 20, 30, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()
    out = optimize_for_web(data, "logo.png")
    result = Image.open(io.BytesIO(out))
    assert result.mode == "RGBA"
    assert max(result.size) <= 1600


def test_never_returns_larger_than_input():
    """Garante a regra 'nunca piorar' mesmo em imagens já pequenas/compactas."""
    data = _make_jpeg(100, 100, quality=40)
    out = optimize_for_web(data, "tiny.jpg")
    assert len(out) <= len(data)


def test_corrupt_data_falls_back_to_original_bytes():
    garbage = b"not an image at all"
    out = optimize_for_web(garbage, "broken.jpg")
    assert out == garbage
