"""O catálogo público nunca fica velho no browser e a versão muda a cada escrita."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from core import cache
from routes.categories import _slugify


def test_bump_changes_catalog_version(monkeypatch):
    monkeypatch.setattr(cache, "get_redis", lambda: None)
    before = cache.catalog_version()
    time.sleep(0.002)
    after = cache.bump_catalog_version()
    assert after != before
    assert cache.catalog_version() == after


def test_invalidate_catalog_change_bumps_version(monkeypatch):
    monkeypatch.setattr(cache, "get_redis", lambda: None)
    before = cache.catalog_version()
    time.sleep(0.002)
    cache.invalidate_catalog_change()  # sem tabela → invalida tudo
    assert cache.catalog_version() != before


def test_version_endpoint_is_never_cached():
    import main

    client = TestClient(main.app, base_url="http://localhost")
    resp = client.get("/catalogo/version", headers={"User-Agent": "Mozilla/5.0 test"})
    assert resp.status_code == 200
    assert resp.json()["v"]
    assert resp.headers["cache-control"] == "no-store"


def test_slugify_matches_storefront_rules():
    assert _slugify("Material de Cozinha") == "material-de-cozinha"
    assert _slugify("Protetor de Colchão") == "protetor-de-colchao"
    assert _slugify("  Óculos ") == "oculos"
    assert _slugify(None) == ""
