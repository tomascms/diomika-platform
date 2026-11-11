/**
 * Leitura do catálogo público da API pela cache da Cloudflare (perto do visitante).
 *
 * A API está numa VM nos EUA: cada pedido directo custava ~200–300 ms só de
 * ida e volta. Aqui as leituras públicas do catálogo ficam em cache no PoP da
 * Cloudflare (Lisboa/Madrid para clientes portugueses) e saem do mesmo domínio
 * da loja — sem CORS nem pedidos OPTIONS.
 *
 * Frescura: a chave da cache inclui a versão do catálogo (GET /catalogo/version,
 * que muda a cada escrita no backoffice). A versão renova-se no máximo de 5 em 5 s por
 * PoP, mas FORA do caminho do pedido (PERF-03): quando expira, o pedido usa já a última
 * versão conhecida e a renovação corre em segundo plano (`waitUntil`). Antes o pedido
 * esperava pela API, nos EUA (0,2–0,6 s), e com pouco tráfego quase todos os visitantes
 * chegavam com a versão expirada. O preço: depois de um período sem visitas, o primeiro
 * pedido ainda vê o catálogo da versão antiga e o seguinte já vê o novo.
 *
 * Resiliência: se a API cair ou ficar lenta (timeouts curtos), usa a última versão
 * conhecida e continua a servir o catálogo em cache. Cada entrada está presa a uma
 * versão (conteúdo imutável), por isso pode viver dias sem ficar desactualizada.
 *
 * Chave: só leva a query que a rota conhece, limpa e ordenada (SEG-12). Antes levava a
 * query inteira, e `?cb=1`, `?cb=2`… atravessavam a cache até à API, uma a uma.
 *
 * Usam-no o proxy `/api` (functions/api/[[path]].js), o mapa do site (functions/sitemap.xml.js) e a
 * recuperação das páginas do catálogo que o build não gerou (functions/_middleware.js): a mesma cache para os três.
 */
export const API_ORIGIN = 'https://api.diomika.com'
const VERSION_TTL_SECONDS = 5
const LAST_VERSION_TTL_SECONDS = 7 * 86400
const ENTRY_TTL_SECONDS = 7 * 86400
const VERSION_TIMEOUT_MS = 2000
const UPSTREAM_TIMEOUT_MS = 8000

/** Os valores que a API aceita, limpos; '' deita o parâmetro fora. */
const clean = {
  number: (value) => (/^\d{1,4}$/.test(value) ? String(Number(value)) : ''),
  term: (value) => value.replace(/\s+/g, ' ').trim().toLowerCase().slice(0, 80),
  option: (value) => (value.length <= 60 ? value.trim() : ''),
}

// Os filtros da família («filter_tipo», «filter_subtipo»…): os mesmos nomes que backend-api/core/catalog_storefront.py aceita.
const FAMILY_FILTER = /^filter_[a-z][a-z0-9_]{0,39}$/

/**
 * As rotas públicas do catálogo que se servem da cache e, para cada uma, os parâmetros de query que a API lê
 * (backend-api/routes/catalog_generic.py): `[nome ou expressão, limpeza]`. Tudo o que não esteja aqui não chega à
 * chave nem à API.
 */
const ROUTES = [
  { path: /^\/categorias$/ },
  { path: /^\/categorias\/slug\/[^/]+$/ },
  { path: /^\/catalogo\/meta$/ },
  {
    path: /^\/catalogo\/search$/,
    params: [
      ['q', clean.term],
      ['limit', clean.number],
    ],
  },
  { path: /^\/catalogo\/modelo-detalhe\/[^/]+$/ },
  {
    path: /^\/catalogo\/[a-z_]+\/modelos-catalogo\/[^/]+$/,
    params: [
      ['limit', clean.number],
      ['offset', clean.number],
      [FAMILY_FILTER, clean.option],
    ],
  },
  { path: /^\/catalogo\/[a-z_]+\/modelo-detalhe\/slug\/[^/]+\/[^/]+$/ },
  { path: /^\/catalogo\/[a-z_]+\/modelo-detalhe\/[^/]+$/ },
]

/** A rota do catálogo que serve este caminho (sem o `/api`), ou undefined. */
export const cacheableRoute = (path) => ROUTES.find((route) => route.path.test(path))

/**
 * A query que a rota conhece, limpa e ordenada: `?filter_tipo=decorativa&limit=50`, ou '' se não sobrar nada. O primeiro
 * valor de cada nome é o que conta.
 */
export function normalizedSearch(route, searchParams) {
  const kept = new Map()
  for (const [name, value] of searchParams) {
    if (kept.has(name)) continue
    const rule = route.params?.find(([wanted]) => (typeof wanted === 'string' ? wanted === name : wanted.test(name)))
    if (rule) kept.set(name, rule[1](value))
  }
  const entries = [...kept].filter(([, value]) => value).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
  const query = new URLSearchParams(entries).toString()
  return query ? `?${query}` : ''
}

/** A API não respondeu (rede, tempo esgotado): quem chama decide se mostra um erro ou se avança sem ela. */
export class UpstreamError extends Error {
  constructor(message = 'Sem ligação ao servidor.') {
    super(message)
    this.name = 'UpstreamError'
  }
}

export function json(status, body, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '0',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      ...extraHeaders
    },
  })
}

function upstreamHeaders(request) {
  const h = new Headers({ Accept: 'application/json', 'User-Agent': 'DiomikaEdge/1.0' })
  const ip = request.headers.get('CF-Connecting-IP')
  if (ip) h.set('X-Forwarded-For', ip)
  return h
}

const cacheText = (value, ttl) =>
  new Response(value, { headers: { 'Cache-Control': `public, max-age=${ttl}` } })

const freshVersionKey = (origin) => new Request(`${origin}/__edge/catalog-version`)
const lastVersionKey = (origin) => new Request(`${origin}/__edge/catalog-version-last`)

async function askVersion(context) {
  const resp = await fetch(`${API_ORIGIN}/catalogo/version`, {
    headers: upstreamHeaders(context.request),
    signal: AbortSignal.timeout(VERSION_TIMEOUT_MS),
  })
  if (!resp.ok) throw new Error(`version ${resp.status}`)
  const { v } = await resp.json()
  const value = String(v || '')
  if (!value) throw new Error('version vazia')
  return value
}

const rememberVersion = (cache, origin, value) =>
  Promise.all([
    cache.put(freshVersionKey(origin), cacheText(value, VERSION_TTL_SECONDS)),
    cache.put(lastVersionKey(origin), cacheText(value, LAST_VERSION_TTL_SECONDS)),
  ])

// A renovação em curso neste isolate: com a versão expirada chegam vários pedidos e a API só precisa de ser perguntada uma vez.
let renewing = null

/** Pergunta a versão à API em segundo plano (`waitUntil`): o pedido que a pediu já foi servido com a última conhecida. */
function renewVersion(context, origin, knownValue) {
  if (renewing) return
  const cache = caches.default
  renewing = askVersion(context)
    .then((value) => rememberVersion(cache, origin, value))
    // API lenta ou em baixo: continua a valer a última conhecida, e só se volta a perguntar daqui a 5 s.
    .catch(() => cache.put(freshVersionKey(origin), cacheText(knownValue, VERSION_TTL_SECONDS)))
    .catch(() => {})
    .finally(() => (renewing = null))
  context.waitUntil(renewing)
}

async function catalogVersion(context, origin) {
  const cache = caches.default
  const fresh = await cache.match(freshVersionKey(origin))
  if (fresh) return fresh.text()

  const last = await cache.match(lastVersionKey(origin))
  if (last) {
    const value = await last.text()
    renewVersion(context, origin, value)
    return value
  }

  // PoP sem nenhuma versão conhecida (o primeiro pedido, ou 7 dias sem visitas): sem versão não há chave de cache.
  try {
    const value = await askVersion(context)
    context.waitUntil(rememberVersion(cache, origin, value))
    return value
  } catch {
    return null
  }
}

/** A resposta que o browser recebe de uma leitura do catálogo (`/api/...`). */
export function forBrowser(body, status, contentType, cacheState) {
  return new Response(body, {
    status,
    headers: {
      'Content-Type': contentType || 'application/json; charset=utf-8',
      'Cache-Control': 'no-cache',
      'X-Edge-Cache': cacheState,
      'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '0',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
    },
  })
}

/**
 * Lê `path` (+ `search`) da API, pela cache. Lança `UpstreamError` se a API não responder.
 * @returns {Promise<{ status: number, body: ArrayBuffer, contentType: string | null, cache: 'HIT' | 'MISS' | 'BYPASS' }>}
 */
export async function catalogFetch(context, path, search = '') {
  const { request } = context
  const origin = new URL(request.url).origin
  const upstreamUrl = `${API_ORIGIN}${path}${search}`
  const version = await catalogVersion(context, origin)
  const cache = caches.default
  const cacheKey = version ? new Request(`${origin}/__edge/v/${version}${path}${search}`) : null

  if (cacheKey) {
    const hit = await cache.match(cacheKey)
    if (hit) {
      return {
        status: hit.status,
        body: await hit.arrayBuffer(),
        contentType: hit.headers.get('Content-Type'),
        cache: 'HIT',
      }
    }
  }

  let upstream
  try {
    upstream = await fetch(upstreamUrl, {
      headers: upstreamHeaders(request),
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    })
  } catch {
    throw new UpstreamError()
  }

  const contentType = upstream.headers.get('Content-Type')
  const body = await upstream.arrayBuffer()
  if (cacheKey && upstream.status === 200) {
    context.waitUntil(
      cache.put(
        cacheKey,
        new Response(body, {
          status: 200,
          headers: { 'Content-Type': contentType || 'application/json', 'Cache-Control': `public, max-age=${ENTRY_TTL_SECONDS}` },
        }),
      ),
    )
  }
  return { status: upstream.status, body, contentType, cache: version ? 'MISS' : 'BYPASS' }
}

/**
 * O JSON de uma rota do catálogo: `{ status, data }`, com `data` só nas respostas 200. Lança `UpstreamError` se a
 * API não responder.
 */
export async function catalogJson(context, path, search = '') {
  const { status, body } = await catalogFetch(context, path, search)
  if (status !== 200) return { status, data: null }
  return { status, data: JSON.parse(new TextDecoder().decode(body)) }
}
