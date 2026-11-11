"""Pesquisa unificada no catálogo público.

Auditoria BR-02, FE-06, RP-07. Antes só procurava no nome e no slug do modelo (e no EAN) com `ilike`: «almofada», o nome
de uma categoria com 2 modelos, dava «Sem resultados»; «colchão» e «colchao» davam resultados diferentes; cores, medidas
e materiais nunca se encontravam; uma gralha não perdoava nada.

Agora a pesquisa corre sobre um índice em memória dos modelos que a loja mostra, com o nome, a categoria, o tipo, a
composição ou os materiais, as cores, as medidas e os EAN de cada um. Compara sem acentos nem maiúsculas, ignora o «s»
final («almofadas»), aceita várias palavras (todas têm de aparecer, cada uma em qualquer campo) e perdoa uma gralha
(«almofda»). O índice tem dezenas de modelos, guarda-se na cache do catálogo e refaz-se quando o catálogo muda
(`invalidate_catalog_change` apaga `catalog:search*`).
"""
from __future__ import annotations

import logging
import re
import unicodedata

from core.cache import catalog_cache_ttl, get_or_set
from core.catalog_storefront import (
    _attach_modelo_cores,
    _flatten_attrs,
    _modelo_cores,
    _visible_products,
    models_detail_map_for_tipo,
)
from core.database import get_db
from core.visibility import is_visible
from models.catalog_attributes import CATEGORY_ATTRIBUTE_SCHEMAS
from models.catalog_registry import tipo_label
from models.schemas import PRODUCT_MODELS_TABLE, PRODUCT_VARIANTS_TABLE

logger = logging.getLogger("diomika-api")

INDEX_CACHE_KEY = "catalog:search-index"

# O PostgREST devolve no máximo 1000 linhas por pedido; o catálogo está longe disso (dezenas de modelos).
_MAX_MODELS = 1000

# Palavras que não dizem o que se procura («toalhas de mesa»): não se exigem a cada modelo.
_STOPWORDS = frozenset({"a", "o", "e", "de", "do", "da", "dos", "das", "em", "para", "com"})

# Peso de cada campo: um EAN exacto ou uma palavra do nome vale mais do que a categoria, e esta mais do que a cor.
_FIELD_WEIGHTS = {"nome": 100, "ean": 90, "categoria": 60, "tipo": 45, "material": 40, "cores": 40, "medidas": 40}


def fold(text: object) -> str:
    """Minúsculas, sem acentos e com «×» como «x»: «Óculos» → «oculos»."""
    folded = unicodedata.normalize("NFD", str(text or "").lower().replace("×", "x"))
    return "".join(ch for ch in folded if unicodedata.category(ch) != "Mn")


def stem(token: str) -> str:
    """Tira o «s» final, para «almofadas» e «almofada» serem a mesma palavra (não mexe em números: EAN, medidas)."""
    if len(token) > 3 and token.endswith("s") and not any(ch.isdigit() for ch in token):
        return token[:-1]
    return token


def tokens(text: object) -> list[str]:
    """As palavras de um texto, comparáveis: sem acentos, medidas «45 x 45» e «32 mm» como «45x45» e «32mm»."""
    folded = fold(text)
    folded = re.sub(r"(?<=\d)\s*x\s*(?=\d)", "x", folded)
    folded = re.sub(r"(?<=\d)\s+(?=(?:mm|cm|m)\b)", "", folded)
    return [stem(word) for word in re.findall(r"[a-z0-9]+", folded)]


# Uma pesquisa de verdade tem poucas palavras e curtas; o resto é lixo que só gastava tempo a comparar.
_MAX_WORDS = 8
_MAX_WORD_LENGTH = 40


def query_tokens(query: object) -> list[str]:
    """As palavras da pesquisa. Se só houver palavras vazias («de»), usam-se todas."""
    words = [word[:_MAX_WORD_LENGTH] for word in tokens(query)]
    return ([w for w in words if w not in _STOPWORDS] or words)[:_MAX_WORDS]


def _within(a: str, b: str, limit: int) -> bool:
    """A distância entre as palavras (inserir, apagar, trocar uma letra, trocar duas seguidas) é no máximo `limit`?"""
    if abs(len(a) - len(b)) > limit:
        return False
    before_previous: list[int] | None = None
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            current[j] = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb))
            if before_previous is not None and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                current[j] = min(current[j], before_previous[j - 2] + 1)
        before_previous, previous = previous, current
    return previous[-1] <= limit


def _quality(word: str, candidate: str, field: str) -> int:
    """Quanto a palavra da pesquisa corresponde à do campo: 3 igual, 2 parte dela, 1 com uma gralha, 0 nada."""
    if word == candidate:
        return 3
    if word.isdigit():
        # Um número solto não é parte de outro: «45» é a medida 45x45 (já vem partida em 45 e 45), não o EAN …6045…
        # Do EAN aceita-se um pedaço com pelo menos 4 dígitos.
        return 2 if field == "ean" and len(word) >= 4 and word in candidate else 0
    if len(word) >= 3 and word in candidate:
        return 2
    # Só palavras (sem dígitos): uma medida ou um EAN com um dígito errado é outra medida, outro artigo.
    if len(word) >= 5 and word.isalpha() and _within(word, candidate, 1 if len(word) < 8 else 2):
        return 1
    return 0


def _score(word: str, document: dict) -> int:
    best = 0
    for field, weight in _FIELD_WEIGHTS.items():
        for candidate in document["campos"].get(field, ()):
            quality = _quality(word, candidate, field)
            if quality * weight > best:
                best = quality * weight
    return best


def rank(documents: list[dict], words: list[str]) -> list[dict]:
    """Os modelos onde aparecem todas as palavras, do que melhor corresponde ao pior; a igualdade desempata por nome."""
    scored = []
    for document in documents:
        scores = [_score(word, document) for word in words]
        if all(scores):
            scored.append((-sum(scores), document["nome"], document))
    scored.sort(key=lambda item: item[:2])
    return [document for _score_, _name, document in scored]


def _kind_labels(tipo: str, flat: dict) -> list[str]:
    """«Decorativa», «Óculos de sol»…: o que os filtros da loja chamam ao valor de cada modelo, mais a família."""
    labels = [tipo_label(tipo)]
    for definition in CATEGORY_ATTRIBUTE_SCHEMAS.get(tipo, {}).get("storefront_filters") or []:
        value = flat.get(definition.get("field"))
        if value:
            labels += [str(value), (definition.get("labels") or {}).get(value, "")]
    return labels


def _document(row: dict, category: dict) -> dict:
    """Um modelo no índice: só texto e números, para ir para a cache (Redis) tal como está."""
    flat = _flatten_attrs(dict(row))
    tipo = str(row.get("tipo_catalogo") or "")
    variants = [_flatten_attrs(dict(variant)) for variant in _visible_products(row.get(PRODUCT_VARIANTS_TABLE))]
    composition = flat.get("composicao")
    materials = list(composition) if isinstance(composition, dict) else []
    materials += [flat.get(name) for name in ("material_forro", "material_enchimento", "material")]
    measures = tokens(" ".join(str(v.get("dimensoes") or v.get("altura") or "") for v in variants))
    # «45x45» procura-se também por «45».
    measures += [part for measure in measures for part in measure.split("x") if "x" in measure and part]

    def unique(words: list[str]) -> list[str]:
        return list(dict.fromkeys(words))

    return {
        "id": str(row["id"]),
        "tipo": tipo,
        "nome": str(row.get("nome") or ""),
        "categoria": {key: category.get(key) for key in ("id", "nome", "slug", "tipo_catalogo")},
        "campos": {
            "nome": unique(tokens(f"{row.get('nome') or ''} {row.get('slug') or ''}")),
            "categoria": unique(tokens(f"{category.get('nome') or ''} {category.get('slug') or ''}")),
            "tipo": unique(tokens(" ".join(str(label) for label in _kind_labels(tipo, flat)))),
            "material": unique(tokens(" ".join(str(m) for m in materials if m))),
            "cores": unique(tokens(" ".join(str(c.get("nome") or "") for c in _modelo_cores(row)))),
            "medidas": unique(measures),
            "ean": unique([str(v["ean"]).strip() for v in variants]),
        },
    }


def build_index() -> list[dict]:
    """Os modelos que a loja mostra (visíveis, com cor e EAN, numa categoria visível), prontos a pesquisar."""
    rows = (
        get_db()
        .table(PRODUCT_MODELS_TABLE)
        .select(
            "id, nome, slug, tipo_catalogo, attributes, "
            "categories(id, nome, slug, tipo_catalogo, visibilidade), "
            f"{PRODUCT_VARIANTS_TABLE}(ean, visibilidade, attributes)"
        )
        .eq("visibilidade", True)
        .range(0, _MAX_MODELS - 1)
        .execute()
        .data
        or []
    )
    _attach_modelo_cores(rows)
    documents = []
    for row in rows:
        category = row.get("categories")
        if isinstance(category, list):
            category = category[0] if category else None
        if not isinstance(category, dict) or not is_visible(category):
            continue
        if _modelo_cores(row) and _visible_products(row.get(PRODUCT_VARIANTS_TABLE)):
            documents.append(_document(row, category))
    return documents


def _cover_path(model: dict) -> str:
    colours = [c for c in (model.get("modelo_cores") or []) if is_visible(c)]
    colours.sort(key=lambda c: c.get("numero", 0))
    return str((colours[0] or {}).get("imagem") or "") if colours else ""


def search_storefront(q: str, *, limit: int = 40) -> list[dict]:
    """Os modelos que correspondem à pesquisa, do melhor para o pior (no máximo `limit`, até 80).

    Cada resultado é `{model, category, cover_path, _tipo_catalogo}`: o detalhe completo do modelo, como a loja o lê.
    """
    limit = min(max(limit, 1), 80)
    words = query_tokens(q)
    if not words:
        return []

    index = get_or_set(INDEX_CACHE_KEY, float(catalog_cache_ttl()), build_index)
    hits = rank(index, words)[:limit]

    ids_by_tipo: dict[str, list[str]] = {}
    for hit in hits:
        ids_by_tipo.setdefault(hit["tipo"], []).append(hit["id"])
    details: dict[str, dict] = {}
    for tipo, ids in ids_by_tipo.items():
        details.update({f"{tipo}:{mid}": detail for mid, detail in models_detail_map_for_tipo(tipo, ids).items()})

    results = []
    for hit in hits:
        detail = details.get(f"{hit['tipo']}:{hit['id']}")
        if detail:  # mudou desde que o índice se fez: o próximo índice já não o traz
            results.append(
                {
                    "model": detail,
                    "category": hit["categoria"],
                    "cover_path": _cover_path(detail),
                    "_tipo_catalogo": hit["tipo"],
                }
            )
    return results
