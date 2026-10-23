"""Tests for shared catalog cache (memory fallback)."""
from __future__ import annotations

from core.cache import cache_backend, get_or_set, invalidate_key, invalidate_prefix


def test_get_or_set_memory():
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return {"ok": True}

    first = get_or_set("test:unit:1", 60, factory)
    second = get_or_set("test:unit:1", 60, factory)
    assert first == second == {"ok": True}
    assert calls["n"] == 1


def test_invalidate_prefix():
    get_or_set("catalog:list:test:1", 60, lambda: [1])
    count = invalidate_prefix("catalog:list:test:")
    assert count >= 1


def test_invalidate_key():
    get_or_set("catalog:meta", 60, lambda: {"v": 1})
    assert invalidate_key("catalog:meta") >= 1


def test_cache_backend_label():
    assert cache_backend() in ("redis", "memory")
