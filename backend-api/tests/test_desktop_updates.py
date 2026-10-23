"""Servir actualizações do backoffice: só ficheiros da pasta, com cache correcta."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import main
    from routes import desktop_updates

    (tmp_path / "latest.yml").write_text("version: 1.2.0\n", encoding="utf-8")
    (tmp_path / "Diomika-Backoffice-1.2.0-setup.exe").write_bytes(b"MZ" + b"\0" * 4096)
    (tmp_path.parent / "secret.txt").write_text("nao", encoding="utf-8")
    monkeypatch.setattr(desktop_updates, "UPDATES_DIR", tmp_path)
    return TestClient(main.app, base_url="http://localhost")


UA = {"User-Agent": "DiomikaBackoffice/1.2"}


def test_manifest_is_served_uncached(client):
    resp = client.get("/system/desktop-updates/latest.yml", headers=UA)
    assert resp.status_code == 200
    assert resp.text.startswith("version: 1.2.0")
    assert resp.headers["cache-control"] == "no-cache"


def test_installer_supports_ranges_without_gzip(client):
    headers = {**UA, "Range": "bytes=0-1", "Accept-Encoding": "gzip"}
    resp = client.get("/system/desktop-updates/Diomika-Backoffice-1.2.0-setup.exe", headers=headers)
    assert resp.status_code == 206
    assert resp.content == b"MZ"
    assert resp.headers.get("content-encoding") == "identity"


def test_head_request(client):
    resp = client.head("/system/desktop-updates/latest.yml", headers=UA)
    assert resp.status_code == 200


@pytest.mark.parametrize("name", ["..%2Fsecret.txt", "missing.yml", ".hidden", "a%5Cb.exe"])
def test_rejects_paths_outside_and_unknown_files(client, name):
    assert client.get(f"/system/desktop-updates/{name}", headers=UA).status_code == 404
