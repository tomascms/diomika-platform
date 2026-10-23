import asyncio
import logging
import re
import unicodedata

from uuid import UUID

from fastapi import APIRouter, HTTPException

from core.cache import catalog_cache_ttl, get_or_set
from core.cqrs.queries.catalog import ListCategoriesQuery, list_categories
from core.database import get_db
from core.public_api import PUBLIC_CATEGORY_FIELDS, public_category
from core.visibility import require_visible

logger = logging.getLogger("diomika-api")

router = APIRouter(prefix="/categorias", tags=["Categorias"])


def _slugify(value) -> str:
    text = unicodedata.normalize("NFD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


@router.get("")
async def get_categories():
    ttl = catalog_cache_ttl()

    def load():
        return list_categories(ListCategoriesQuery())

    try:
        return await asyncio.to_thread(get_or_set, "categories:all", float(ttl), load)
    except Exception as e:
        logger.error("Erro ao listar categorias: %s", e)
        raise HTTPException(status_code=500, detail="Erro ao carregar categorias") from e


@router.get("/slug/{slug}")
async def get_category_by_slug(slug: str):
    ttl = catalog_cache_ttl()
    cache_key = f"categories:slug:{slug}"

    def load():
        wanted = slug.strip()
        res = get_db().table("categories").select(PUBLIC_CATEGORY_FIELDS).eq("slug", wanted).execute()
        rows = res.data or []
        if not rows:
            # Também aceita o slug derivado do nome («material-de-cozinha» para
            # «Material de Cozinha»): links antigos ou escritos à mão não dão 404.
            wanted_norm = _slugify(wanted)
            all_rows = get_db().table("categories").select(PUBLIC_CATEGORY_FIELDS).execute().data or []
            rows = [r for r in all_rows if _slugify(r.get("nome")) == wanted_norm or _slugify(r.get("slug")) == wanted_norm]
        if not rows:
            raise HTTPException(status_code=404, detail="Categoria não encontrada")
        return public_category(require_visible(rows[0]))

    try:
        return await asyncio.to_thread(get_or_set, cache_key, float(ttl), load)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao buscar categoria slug %s: %s", slug, e)
        raise HTTPException(status_code=500, detail="Erro ao carregar categoria") from e


@router.get("/{id_categoria}")
async def get_category(id_categoria: UUID):
    ttl = catalog_cache_ttl()
    cache_key = f"categories:{id_categoria}"

    def load():
        res = get_db().table("categories").select(PUBLIC_CATEGORY_FIELDS).eq("id", str(id_categoria)).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="ID não encontrado")
        return public_category(require_visible(res.data[0]))

    try:
        return await asyncio.to_thread(get_or_set, cache_key, float(ttl), load)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao buscar categoria %s: %s", id_categoria, e)
        raise HTTPException(status_code=500, detail="Erro ao carregar categoria") from e
