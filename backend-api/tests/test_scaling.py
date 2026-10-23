"""Testes de cache e rate limit tiered."""
from __future__ import annotations

from core.cache import get_or_set, invalidate_prefix
from core.path_patterns import is_public_catalog_path
from core.rate_limit import _limits_for_path


def test_catalog_read_detection():
    assert is_public_catalog_path("/categorias")
    assert is_public_catalog_path("/catalogo/meta")
    assert is_public_catalog_path("/catalogo/almofadas/modelos-catalogo/x")
    assert not is_public_catalog_path("/categoriasx")
    assert not is_public_catalog_path("/contacto")
    assert _limits_for_path("POST", "/categorias")[0] == "global"


def test_tiered_limits():
    assert _limits_for_path("GET", "/categorias")[0] == "catalog"
    assert _limits_for_path("GET", "/admin/crud/categories")[0] == "admin"
    assert _limits_for_path("POST", "/contacto")[0] == "global"


def test_ttl_cache():
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return {"v": calls["n"]}

    assert get_or_set("k1", 60.0, factory) == {"v": 1}
    assert get_or_set("k1", 60.0, factory) == {"v": 1}
    assert calls["n"] == 1
    invalidate_prefix("k1")
    assert get_or_set("k1", 60.0, factory) == {"v": 2}


def test_catalog_rate_limit_higher_than_global():
    import uuid

    from core.rate_limit import _record_and_check

    suffix = uuid.uuid4().hex[:8]
    key_cat = f"catalog:test-{suffix}"
    key_glob = f"global:test-{suffix}"
    for _ in range(120):
        assert _record_and_check(key_glob, 120, 60)
    assert not _record_and_check(key_glob, 120, 60)
    for _ in range(300):
        assert _record_and_check(key_cat, 600, 60)
