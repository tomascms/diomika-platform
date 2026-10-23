"""Upload grava também a miniatura WebP usada nas listas da loja."""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

from PIL import Image

from utils import storage
from utils.image_resize import make_thumbnail, thumb_path


def _jpeg(w=1500, h=1125) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 30, 30)).save(buf, format="JPEG")
    return buf.getvalue()


def test_thumbnail_is_small_webp():
    thumb = make_thumbnail(_jpeg(), "a.jpg")
    img = Image.open(io.BytesIO(thumb))
    assert img.format == "WEBP" and img.width == 480


def test_thumb_path_keeps_original_recoverable():
    assert thumb_path("categories/imagem/x.png") == "categories/imagem/x.png.w480.webp"


def test_upload_writes_original_and_thumbnail(monkeypatch):
    monkeypatch.delenv("SUPABASE_STORAGE_PRIVATE", raising=False)
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    bucket = MagicMock()
    bucket.get_public_url.return_value = "https://x/storage/v1/object/public/product-images/m/a.jpg"
    db = MagicMock()
    db.storage.from_.return_value = bucket
    with patch.object(storage, "get_db", return_value=db):
        storage.upload_bytes(_jpeg(), "m/a.jpg", "image/jpeg")
    paths = [c.args[0] for c in bucket.upload.call_args_list]
    assert paths == ["m/a.jpg", "m/a.jpg.w480.webp", "m/a.jpg.w960.webp"]


def test_large_thumbnail_width():
    img = Image.open(io.BytesIO(make_thumbnail(_jpeg(), "a.jpg", width=960)))
    assert img.width == 960
