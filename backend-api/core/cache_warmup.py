"""Pré-aquece cache Redis após arranque — 1.º visitante não paga cold start."""
from __future__ import annotations

import logging
import re
import threading
import unicodedata

logger = logging.getLogger("diomika-api")


def warm_catalog_cache() -> None:
    from core.cache import catalog_cache_ttl, get_or_set
    from core.cqrs.queries.catalog import ListCategoriesQuery, list_categories
    from models.catalog_registry import catalog_metadata

    ttl = float(catalog_cache_ttl())
    try:
        get_or_set("categories:all", ttl, lambda: list_categories(ListCategoriesQuery()))
        get_or_set("catalog:meta", ttl, catalog_metadata)
        logger.info("Cache catálogo pré-aquecido (categories + meta, ttl=%ss)", int(ttl))
    except Exception as exc:
        logger.warning("Warm cache falhou (não crítico): %s", exc)


_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", re.I)
_warm_lock = threading.Lock()


def slugify(value: object) -> str:
    """Igual a slugifyName (frontend-web/src/lib/catalogRoutes.js): as chaves de cache
    têm de bater com os URLs que a loja pede."""
    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if not ("̀" <= ch <= "ͯ"))
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def _category_slug(cat: dict) -> str:
    slug = str(cat.get("slug") or "").strip()
    return slug if slug and not _UUID.fullmatch(slug) else slugify(cat.get("nome"))


def _model_slug(model: dict) -> str:
    slug = str(model.get("slug") or "")
    return slugify(model.get("nome")) or (slug if slug and not _UUID.fullmatch(slug) else "")


def warm_model_details() -> int:
    """Detalhe de cada modelo visível em Redis: o 1.º visitante de cada página de produto
    não espera pelas várias consultas EUA→Irlanda (~1 s). Devolve quantos aqueceu."""
    from core.cache import catalog_cache_ttl, get_or_set
    from core.catalog_service import model_detail_for_slugs
    from core.database import get_db
    from models.schemas import PRODUCT_MODELS_TABLE

    if not _warm_lock.acquire(blocking=False):
        return 0  # já há um aquecimento a correr
    warmed = 0
    try:
        ttl = float(catalog_cache_ttl())
        db = get_db()
        cats = db.table("categories").select("id,nome,slug,tipo_catalogo,visibilidade").execute().data or []
        for cat in cats:
            tipo = cat.get("tipo_catalogo")
            if cat.get("visibilidade") is False or not tipo:
                continue
            cslug = _category_slug(cat)
            models = (
                db.table(PRODUCT_MODELS_TABLE).select("nome,slug")
                .eq("id_categoria", cat["id"]).eq("visibilidade", True).execute().data or []
            )
            for m in models:
                mslug = _model_slug(m)
                if not mslug:
                    continue
                key = f"catalog:modelo-slug:{tipo}:{cslug}:{mslug}"
                def load(t=tipo, c=cslug, s=mslug):
                    data = model_detail_for_slugs(t, c, s)
                    if not data:
                        raise LookupError("sem detalhe")  # nunca guardar null (a rota daria 200 vazio)
                    return data

                try:
                    get_or_set(key, ttl, load)
                    warmed += 1
                except LookupError:
                    continue
                except Exception:
                    logger.warning("Warm do detalhe %s falhou", key, exc_info=True)
        logger.info("Cache: %d detalhes de modelo pré-aquecidos", warmed)
    except Exception:
        logger.warning("Warm dos detalhes falhou (não crítico)", exc_info=True)
    finally:
        _warm_lock.release()
    return warmed


def warmup_enabled() -> bool:
    import os

    return os.getenv("DIOMIKA_WARMUP", "1") != "0"  # tests/conftest.py desliga


def warm_model_details_in_background() -> None:
    if not warmup_enabled():
        return
    threading.Thread(target=warm_model_details, name="warm-details", daemon=True).start()
