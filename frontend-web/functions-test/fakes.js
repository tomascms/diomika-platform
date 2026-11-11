// Peças para testar as Pages Functions (functions/) em Node, sem Cloudflare: a cache do PoP (`caches.default`), a API
// (o `fetch` global, que só conhece api.diomika.com e responde com as fixtures do e2e) e o contexto de um pedido.
// Os testes ficam fora de functions/ para o Pages nunca os tomar por rotas.
import { readFileSync } from 'node:fs'

const FIXTURES = new URL('../e2e/local/fixtures/', import.meta.url)
const readFixture = (name) => JSON.parse(readFileSync(new URL(`${name}.json`, FIXTURES), 'utf8'))

/** A cache do PoP: guarda a resposta pelo URL do pedido, sem prazos (os testes dizem quando há de esvaziar-se). */
export function fakeCache() {
  const entries = new Map()
  return {
    entries,
    match: async (request) => entries.get(new Request(request).url)?.clone(),
    put: async (request, response) => void entries.set(new Request(request).url, response.clone()),
  }
}

const ok = (data) => ({ status: 200, data })

/**
 * A API de produção, com as fixtures. `overrides` troca uma resposta ({ '/categorias': () => ({ status, data }) }).
 * `edge.apiCalls` lista os pedidos que chegaram à API (caminho e query); `edge.fail = true` simula-a em baixo;
 * `edge.version` é a versão do catálogo que a API anuncia, e a resposta só sai quando `edge.versionGate` se resolve
 * (por omissão já está): para um teste segurar a API da versão e ver o que a loja faz entretanto.
 */
export function installEdge(overrides = {}) {
  const edge = { apiCalls: [], fail: false, version: 'v1', versionGate: Promise.resolve(), cache: fakeCache() }
  const routes = {
    '/catalogo/version': async () => {
      await edge.versionGate
      return ok({ v: edge.version })
    },
    '/categorias': () => ok(readFixture('categorias')),
    ...overrides,
  }
  const original = { fetch: globalThis.fetch, caches: globalThis.caches }
  globalThis.caches = { default: edge.cache }
  globalThis.fetch = async (input) => {
    const url = new URL(typeof input === 'string' ? input : input.url)
    if (url.hostname !== 'api.diomika.com') throw new Error(`pedido para fora da API: ${url}`)
    edge.apiCalls.push(url.pathname + url.search)
    if (edge.fail) throw new TypeError('fetch failed')
    let answer = await routes[url.pathname]?.(url)
    if (!answer) {
      const list = /^\/catalogo\/([a-z_]+)\/modelos-catalogo\/([^/]+)$/.exec(url.pathname)
      try {
        answer = list ? ok(readFixture(`catalogo/${list[1]}/modelos-catalogo/${list[2]}`)) : null
      } catch {
        answer = null
      }
    }
    answer ??= { status: 404, data: { detail: 'Não encontrado' } }
    return new Response(JSON.stringify(answer.data), {
      status: answer.status,
      headers: { 'Content-Type': 'application/json' },
    })
  }
  edge.restore = () => {
    globalThis.fetch = original.fetch
    globalThis.caches = original.caches
  }
  return edge
}

/** A loja pré-renderizada (`/`) e um 404 do Pages: o que `env.ASSETS` e `context.next()` dão. */
export const SHELL_HTML =
  '<!doctype html><html><head><title>Diomika</title>' +
  '<link rel="canonical" href="https://www.diomika.com/">' +
  '<meta property="og:url" content="https://www.diomika.com/"></head>' +
  '<body><div id="app"></div></body></html>'
export const NOT_FOUND_HTML = '<!doctype html><title>Página não encontrada</title><h1>404</h1>'

/** `files`: caminho → conteúdo (o que existe no `dist`). O resto dá o 404 estático, como o Pages. */
export function fakeAssets(files = { '/': SHELL_HTML }) {
  const requested = []
  const fetch = async (request) => {
    const { pathname } = new URL(request.url)
    requested.push(pathname)
    // Como o Pages: um ficheiro que existe, pedido com `If-None-Match`, responde 304 sem corpo.
    if (pathname in files && request.headers.has('If-None-Match')) return new Response(null, { status: 304 })
    if (pathname in files) {
      return new Response(files[pathname], {
        status: 200,
        headers: { 'Content-Type': 'text/html; charset=utf-8', 'Content-Length': String(files[pathname].length) },
      })
    }
    return new Response(NOT_FOUND_HTML, {
      status: 404,
      headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' },
    })
  }
  return { fetch, requested }
}

/**
 * O contexto de um pedido às Functions. `waitUntil` guarda as promessas: `await ctx.settled()` espera por elas
 * (a escrita na cache acontece depois de a resposta sair).
 */
export function pagesContext(url, { method = 'GET', headers = {}, assets = fakeAssets() } = {}) {
  const pending = []
  const request = new Request(url, { method, headers })
  const context = {
    request,
    env: { ASSETS: assets },
    waitUntil: (promise) => void pending.push(promise),
    // O que o Pages faz com um pedido que as Functions deixam passar: procura o ficheiro.
    next: async () => assets.fetch(request),
    settled: () => Promise.all(pending),
  }
  return context
}
