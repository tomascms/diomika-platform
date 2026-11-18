"""Fotos de telemóvel (2–15 MB) entram no upload de imagem; o resto da API mantém o limite de 2 MB."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.middleware import BodySizeLimitMiddleware

app = FastAPI()
app.add_middleware(BodySizeLimitMiddleware)


@app.post("/admin/crud/upload-image")
@app.post("/admin/crud/outra")
async def _ok():
    return {"ok": True}


client = TestClient(app)
PHOTO = b"x" * (6 * 1024 * 1024)


def test_photo_upload_passes_the_global_limit():
    assert client.post("/admin/crud/upload-image", content=PHOTO).status_code == 200


def test_other_routes_keep_2mb():
    assert client.post("/admin/crud/outra", content=PHOTO).status_code == 413


def test_upload_still_has_a_ceiling():
    assert client.post("/admin/crud/upload-image", content=b"x" * (17 * 1024 * 1024)).status_code == 413
