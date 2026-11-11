"""O `barcode_url` gravado na BD é o URL público, que não expira (auditoria SEO-07, FE-10).

Antes gravava-se o que `upload_bytes` devolve: com o bucket privado é um URL assinado, com `token=` e validade. Fica na
BD para sempre e deixa de abrir (11 produtos da loja mostravam a imagem partida). O bucket de produção é público e o
caminho público abre; num bucket privado a loja volta a assinar a partir do caminho do objecto.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

SIGNED = "https://abc.supabase.co/storage/v1/object/sign/product-images/barcodes/5606044501371.png?token=jwt.abc.def"
PUBLIC = "https://abc.supabase.co/storage/v1/object/public/product-images/barcodes/5606044501371.png"


def _storage_db() -> MagicMock:
    bucket = MagicMock()
    bucket.create_signed_url.return_value = {"signedURL": SIGNED}
    bucket.get_public_url.return_value = PUBLIC
    db = MagicMock()
    db.storage.from_.return_value = bucket
    return db


def test_barcode_url_is_public_even_when_the_bucket_is_private(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "supabase")
    monkeypatch.setenv("SUPABASE_STORAGE_PRIVATE", "1")
    from utils import barcode_gen, storage

    db = _storage_db()
    with patch.object(storage, "get_db", return_value=db):
        # A prova de que o teste apanha o erro: o URL de entrega de um bucket privado é o assinado.
        assert storage.resolve_delivery_url("barcodes/5606044501371.png") == SIGNED
        url, ean = barcode_gen.generate_ean13("5606044501371")

    assert (url, ean) == (PUBLIC, "5606044501371")
    assert "token=" not in url and "/object/sign/" not in url
    uploaded = db.storage.from_.return_value.upload.call_args
    assert uploaded.args[0] == "barcodes/5606044501371.png"


def test_barcode_url_is_public_with_a_public_bucket(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "supabase")
    monkeypatch.delenv("SUPABASE_STORAGE_PRIVATE", raising=False)
    from utils import barcode_gen, storage

    with patch.object(storage, "get_db", return_value=_storage_db()):
        data: dict = {"ean": "5606044501371"}
        barcode_gen.apply_barcode_url(data)

    assert data["barcode_url"] == PUBLIC


def test_wrong_check_digit_still_names_the_right_one(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "supabase")
    from utils import barcode_gen, storage

    with patch.object(storage, "get_db", return_value=_storage_db()) as get_db:
        assert barcode_gen.generate_ean13("5606044501372") == ("INVALID_CHECKSUM", "5606044501371")
    get_db.assert_not_called()  # nada foi enviado para o Storage
