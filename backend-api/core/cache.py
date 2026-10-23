"""Cache partilhado (Redis) com fallback in-process por worker."""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Callable, TypeVar

from core.redis_client import get_redis, redis_available

logger = logging.getLogger("diomika-api")

T = TypeVar("T")

_lock = threading.Lock()
_store: dict[str, tuple[float, Any]] = {}
_REDIS_PREFIX = "diomika:cache:"
_hits = 0
_misses = 0


def catalog_cache_ttl() -> int:
    return max(60, int(os.getenv("CATALOG_CACHE_TTL", "3600")))


def cache_backend() -> str:
    return "redis" if redis_available() else "memory"


def cache_stats() -> dict[str, int | str]:
    return {"backend": cache_backend(), "hits": _hits, "misses": _misses}


def _redis_key(key: str) -> str:
    return f"{_REDIS_PREFIX}{key}"


def _memory_get(key: str) -> Any | None:
    now = time.monotonic()
    with _lock:
        entry = _store.get(key)
        if entry and entry[0] > now:
            return entry[1]
    return None


def _memory_set(key: str, value: Any, ttl_seconds: float) -> None:
    expires = time.monotonic() + ttl_seconds
    with _lock:
        _store[key] = (expires, value)
        if len(_store) > 4000:
            _purge_memory(time.monotonic())


def get_or_set(key: str, ttl_seconds: float, factory: Callable[[], T]) -> T:
    global _hits, _misses

    client = get_redis()
    if client is not None:
        rkey = _redis_key(key)
        try:
            raw = client.get(rkey)
            if raw is not None:
                _hits += 1
                return json.loads(raw)
        except Exception as exc:
            logger.debug("Redis cache read falhou (%s): %s", key, exc)

    cached = _memory_get(key)
    if cached is not None:
        _hits += 1
        return cached  # type: ignore[return-value]

    _misses += 1
    value = factory()

    if client is not None:
        try:
            client.setex(rkey, max(1, int(ttl_seconds)), json.dumps(value, default=str))
        except Exception as exc:
            logger.debug("Redis cache write falhou (%s): %s", key, exc)

    _memory_set(key, value, ttl_seconds)
    return value


def invalidate_key(key: str) -> int:
    count = 0
    client = get_redis()
    if client is not None:
        try:
            count += int(client.delete(_redis_key(key)))
        except Exception:
            logger.warning("Redis: invalidação de %s falhou (a loja pode mostrar dados antigos)", key, exc_info=True)
    with _lock:
        if key in _store:
            del _store[key]
            count += 1
    return count


def invalidate_prefix(prefix: str) -> int:
    count = 0
    client = get_redis()
    if client is not None:
        pattern = f"{_REDIS_PREFIX}{prefix}*"
        try:
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor=cursor, match=pattern, count=200)
                if keys:
                    count += client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:
            logger.debug("Redis invalidate_prefix falhou (%s): %s", prefix, exc)

    with _lock:
        keys = [k for k in _store if k.startswith(prefix)]
        for k in keys:
            del _store[k]
        count += len(keys)
    return count


_VERSION_KEY = "catalog:version"
_local_version = str(int(time.time() * 1000))


def catalog_version() -> str:
    """Versão actual do catálogo público — muda a cada escrita no backoffice.

    A cache da Cloudflare (functions/api na loja) usa-a na chave: depois de
    publicar, a versão muda e a loja deixa de servir a cópia antiga em segundos.
    Fica no Redis para os workers do uvicorn concordarem; sem Redis cada worker
    tem a sua (a edge só perde eficiência, nunca serve dados velhos).
    """
    client = get_redis()
    if client is not None:
        try:
            key = _redis_key(_VERSION_KEY)
            value = client.get(key)
            if value is None:
                client.set(key, _local_version, nx=True)
                value = client.get(key)
            if value is not None:
                return value.decode() if isinstance(value, bytes) else str(value)
        except Exception as exc:
            logger.debug("Redis catalog_version falhou: %s", exc)
    return _local_version


def bump_catalog_version() -> str:
    global _local_version
    new_value = str(int(time.time() * 1000))
    _local_version = new_value
    client = get_redis()
    if client is not None:
        try:
            client.set(_redis_key(_VERSION_KEY), new_value)
        except Exception as exc:
            logger.debug("Redis bump_catalog_version falhou: %s", exc)
    return new_value


def _purge_memory(now: float) -> None:
    expired = [k for k, (exp, _) in _store.items() if exp <= now]
    for k in expired:
        del _store[k]
    if len(_store) > 3000:
        for k in list(_store.keys())[: len(_store) - 2000]:
            del _store[k]


def _rewarm_details_later() -> None:
    """Depois de uma escrita no backoffice, volta a aquecer os detalhes (em fundo, só produção)."""
    from core.config import get_settings

    from core.cache_warmup import warm_model_details, warmup_enabled

    if not get_settings().is_production or not warmup_enabled():
        return
    import threading

    # 5 s: deixa terminar as invalidações deste pedido (e de escritas em série) antes de reaquecer.
    threading.Timer(5.0, warm_model_details).start()


def invalidate_catalog_change(
    *,
    table_name: str | None = None,
    record: dict | None = None,
    record_id: str | None = None,
) -> None:
    """Invalidação cirúrgica após writes admin — limpa listas/modelos afectados."""
    from core.database import get_db
    from models.catalog_registry import (
        all_colors_tables,
        all_model_tables,
        all_product_tables,
        physical_table_for,
        tipo_for_table,
    )
    from models.schemas import CATEGORY_DEFINITIONS

    bump_catalog_version()
    invalidate_prefix("admin:merged:")
    invalidate_key("catalog:meta")
    _rewarm_details_later()

    if not table_name:
        invalidate_prefix("categories:")
        invalidate_prefix("catalog:")
        return

    db = get_db()
    row = dict(record or {})
    rid = str(record_id or row.get("id") or "").strip()

    def _virtual_tipos(physical: str) -> list[str]:
        out: list[str] = []
        for definition in CATEGORY_DEFINITIONS.values():
            agg = definition.get("aggregated_tipos") or []
            if physical in agg:
                virtual = definition.get("tipo_catalogo")
                if virtual:
                    out.append(str(virtual))
        return out

    def _invalidate_listings(tipo: str | None, id_categoria: str | None) -> None:
        if not tipo or not id_categoria:
            return
        invalidate_prefix(f"catalog:list:{tipo}:{id_categoria}")
        for virtual in _virtual_tipos(tipo):
            invalidate_prefix(f"catalog:list:{virtual}:{id_categoria}")

    def _invalidate_model(tipo: str | None, id_modelo: str | None) -> None:
        if not id_modelo:
            return
        invalidate_key(f"catalog:modelo-auto:{id_modelo}")
        invalidate_prefix("catalog:modelo-slug:")
        if tipo:
            invalidate_key(f"catalog:modelo:{tipo}:{id_modelo}")

    if table_name == "categories":
        invalidate_prefix("categories:")
        invalidate_prefix("catalog:list:")
        if rid:
            invalidate_prefix(f"catalog:list:")
        return

    tipo = tipo_for_table(table_name)
    physical = physical_table_for(table_name)

    if table_name in all_model_tables():
        id_categoria = str(row.get("id_categoria") or "").strip()
        if not id_categoria and rid:
            fetched = db.table(physical).select("id_categoria").eq("id", rid).limit(1).execute().data
            id_categoria = str((fetched or [{}])[0].get("id_categoria") or "")
        _invalidate_listings(tipo, id_categoria or None)
        _invalidate_model(tipo, rid or None)
        return

    if table_name in all_product_tables() or table_name in all_colors_tables():
        id_modelo = str(row.get("id_modelo") or "").strip()
        if not id_modelo and rid:
            fetched = db.table(physical).select("id_modelo").eq("id", rid).limit(1).execute().data
            id_modelo = str((fetched or [{}])[0].get("id_modelo") or "")
        id_categoria = ""
        if id_modelo:
            from models.schemas import PRODUCT_MODELS_TABLE

            fetched = db.table(PRODUCT_MODELS_TABLE).select("id_categoria").eq("id", id_modelo).limit(1).execute().data
            id_categoria = str((fetched or [{}])[0].get("id_categoria") or "")
            _invalidate_model(tipo, id_modelo)
        _invalidate_listings(tipo, id_categoria or None)
        return

    invalidate_prefix("catalog:")
