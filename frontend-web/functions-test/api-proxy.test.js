import { afterEach, beforeEach, describe, test } from 'node:test'
import assert from 'node:assert/strict'
import { onRequest } from '../functions/api/[[path]].js'
import { installEdge, pagesContext } from './fakes.js'

let edge
beforeEach(() => void (edge = installEdge()))
afterEach(() => edge.restore())

const get = async (path, options) => {
  const context = pagesContext(`https://www.diomika.com${path}`, options)
  const response = await onRequest(context)
  await context.settled() // a escrita na cache acontece depois de a resposta sair
  return response
}

const ALMOFADAS = '/catalogo/almofada/modelos-catalogo/4bba6298-b2d8-4d80-9303-49118f2bb29c'
const VERSION = '/catalogo/version'
const versionCalls = () => edge.apiCalls.filter((call) => call === VERSION).length
/** A versão do catálogo que a cache do PoP guarda por 5 s expirou; a última conhecida (7 dias) fica. */
const expireFreshVersion = () => edge.cache.entries.delete('https://www.diomika.com/__edge/catalog-version')
const watch = (promise) => {
  const state = { settled: false }
  promise.then(() => (state.settled = true))
  return state
}
const tick = () => new Promise((resolve) => setTimeout(resolve, 20))
/** A API muda (a da versão, por exemplo) mas o PoP, com a sua cache, é o mesmo. */
const changeApi = (overrides) => {
  const cache = edge.cache
  edge.restore()
  edge = installEdge(overrides)
  edge.cache = cache
  globalThis.caches = { default: cache }
}

describe('proxy /api da loja: leituras públicas do catálogo', () => {
  test('a primeira leitura vai à API (MISS) e a seguinte sai da cache (HIT), sem tocar na API', async () => {
    const first = await get('/api/categorias')
    const callsAfterFirst = [...edge.apiCalls]
    const second = await get('/api/categorias')

    assert.equal(first.status, 200)
    assert.equal(first.headers.get('x-edge-cache'), 'MISS')
    assert.equal(second.headers.get('x-edge-cache'), 'HIT')
    assert.deepEqual(await second.json(), await first.json())
    assert.deepEqual(edge.apiCalls, callsAfterFirst)
  })

  test('uma versão nova do catálogo deixa de servir a cópia antiga', async () => {
    await get('/api/categorias')
    edge.version = 'v2'
    // A versão está em cache 5 s por PoP: depois disso volta a perguntar.
    for (const key of edge.cache.entries.keys()) {
      if (key.includes('__edge/catalog-version')) edge.cache.entries.delete(key)
    }

    const response = await get('/api/categorias')

    assert.equal(response.headers.get('x-edge-cache'), 'MISS')
  })

  test('só GET e HEAD: um POST leva 405', async () => {
    const response = await get('/api/categorias', { method: 'POST' })

    assert.equal(response.status, 405)
    assert.equal(response.headers.get('allow'), 'GET, HEAD')
    assert.deepEqual(edge.apiCalls, [])
  })

  test('só as rotas públicas do catálogo: o resto dá 404 sem ir à API', async () => {
    for (const path of ['/api/admin/crud/categories', '/api/orcamentos', '/api/health', '/api/']) {
      const response = await get(path)
      assert.equal(response.status, 404, path)
    }
    assert.deepEqual(edge.apiCalls, [])
  })

  test('com a API em baixo e sem cache, devolve 502 com uma mensagem em português', async () => {
    edge.fail = true

    const response = await get('/api/categorias')

    assert.equal(response.status, 502)
    assert.match((await response.json()).detail, /Sem ligação ao servidor/)
  })

  test('a resposta de erro da API passa tal como veio e não fica em cache', async () => {
    const response = await get('/api/categorias/slug/nao-existe')
    await get('/api/categorias/slug/nao-existe')

    assert.equal(response.status, 404)
    assert.equal(edge.apiCalls.filter((call) => call.includes('/categorias/slug/nao-existe')).length, 2)
  })
})

describe('chave da cache sem query arbitrária (SEG-12)', () => {
  test('uma query inventada não fura a cache: todas as variantes de /categorias são a mesma entrada', async () => {
    const first = await get('/api/categorias?cb=1')
    const second = await get('/api/categorias?cb=2&utm_source=x')
    const third = await get('/api/categorias')

    assert.equal(first.headers.get('x-edge-cache'), 'MISS')
    assert.equal(second.headers.get('x-edge-cache'), 'HIT')
    assert.equal(third.headers.get('x-edge-cache'), 'HIT')
    // À API só chegou um pedido, e sem a query (nem a chave nem o pedido levam o que a rota não conhece).
    assert.deepEqual(edge.apiCalls.filter((call) => call.startsWith('/categorias')), ['/categorias'])
  })

  test('a query é reconstruída só com os parâmetros que a rota conhece, ordenados, para a chave e para a API', async () => {
    changeApi({ '/catalogo/search': () => ({ status: 200, data: [] }) })
    await get('/api/catalogo/search?zz=1&q=%20Almofada%20&limit=040&cb=9')
    const again = await get('/api/catalogo/search?limit=40&q=almofada')

    assert.deepEqual(edge.apiCalls.filter((call) => call.startsWith('/catalogo/search')), ['/catalogo/search?limit=40&q=almofada'])
    assert.equal(again.headers.get('x-edge-cache'), 'HIT')
  })

  test('a lista de modelos de uma categoria aceita limit, offset, filter_tipo e os filtros da família', async () => {
    await get(`/api${ALMOFADAS}?limit=50&evil=1&filter_tipo=decorativa&offset=0&filter_BAD=1&filter_foo=bar`)

    assert.deepEqual(
      edge.apiCalls.filter((call) => call.startsWith(ALMOFADAS)),
      [`${ALMOFADAS}?filter_foo=bar&filter_tipo=decorativa&limit=50&offset=0`],
    )
  })

  test('valores sem sentido saem: números que não o são, ou enormes, e termos vazios; os longos cortam-se', async () => {
    await get('/api/catalogo/search?q=%20%20&limit=abc&offset=-1')
    await get(`/api/catalogo/search?q=${'a'.repeat(300)}&limit=99999`)
    await get(`/api${ALMOFADAS}?limit=1.5&filter_tipo=&filter_foo=${'x'.repeat(200)}`)

    const asked = edge.apiCalls.filter((call) => /^\/catalogo\/(search|almofada)/.test(call))
    assert.deepEqual(asked, ['/catalogo/search', `/catalogo/search?q=${'a'.repeat(80)}`, ALMOFADAS])
  })

  test('as rotas sem parâmetros ignoram a query toda', async () => {
    await get('/api/categorias/slug/almofada?x=1')
    await get('/api/catalogo/meta?x=1')

    assert.deepEqual(edge.apiCalls.filter((call) => /slug|meta/.test(call)), ['/categorias/slug/almofada', '/catalogo/meta'])
  })

  test('o mesmo parâmetro repetido conta uma vez (o primeiro)', async () => {
    await get('/api/catalogo/search?q=azul&q=vermelho')

    assert.deepEqual(edge.apiCalls.filter((call) => call.startsWith('/catalogo/search')), ['/catalogo/search?q=azul'])
  })
})

// Com prazo: se a resposta ficar à espera da API da versão (o que o PERF-03 descreve), o teste falha em vez de ficar pendurado.
describe('a versão do catálogo fora do caminho do pedido (PERF-03)', { timeout: 3000 }, () => {
  test('com a versão expirada serve já a cache da última versão conhecida, sem esperar pela API da versão', async () => {
    await get('/api/categorias') // o PoP aprende a versão e guarda a lista
    expireFreshVersion()
    let release
    edge.versionGate = new Promise((resolve) => (release = resolve))
    const callsBefore = versionCalls()

    const context = pagesContext('https://www.diomika.com/api/categorias')
    const response = await onRequest(context) // não fica à espera da versão: a API da versão está parada

    assert.equal(response.status, 200)
    assert.equal(response.headers.get('x-edge-cache'), 'HIT')
    assert.equal(versionCalls(), callsBefore + 1) // a renovação já começou, em segundo plano…
    edge.version = 'v2'
    release()
    await context.settled() // …e acaba depois da resposta
    const fresh = await edge.cache.match(new Request('https://www.diomika.com/__edge/catalog-version'))
    assert.equal(await fresh.text(), 'v2')
  })

  test('depois da renovação o catálogo novo aparece: a chave passa a ser a da versão nova', async () => {
    await get('/api/categorias')
    expireFreshVersion()
    edge.version = 'v2'
    await get('/api/categorias') // serve v1 e renova para v2

    const response = await get('/api/categorias')

    assert.equal(response.headers.get('x-edge-cache'), 'MISS')
    assert.equal(edge.apiCalls.filter((call) => call === '/categorias').length, 2)
  })

  test('vários pedidos com a versão expirada renovam-na uma só vez', async () => {
    await get('/api/categorias')
    expireFreshVersion()
    const callsBefore = versionCalls()
    let release
    edge.versionGate = new Promise((resolve) => (release = resolve))
    const contexts = Array.from({ length: 5 }, () => pagesContext('https://www.diomika.com/api/categorias'))

    const responses = await Promise.all(contexts.map((context) => onRequest(context)))
    release()
    await Promise.all(contexts.map((context) => context.settled()))

    assert.deepEqual(responses.map((response) => response.headers.get('x-edge-cache')), Array(5).fill('HIT'))
    assert.equal(versionCalls(), callsBefore + 1)
  })

  test('um PoP que ainda não conhece nenhuma versão tem de a pedir antes de servir', async () => {
    let release
    edge.versionGate = new Promise((resolve) => (release = resolve))
    const context = pagesContext('https://www.diomika.com/api/categorias')

    const pending = onRequest(context)
    const state = watch(pending)
    await tick()
    assert.equal(state.settled, false) // sem versão não há chave de cache: espera
    release()
    const response = await pending
    await context.settled()

    assert.equal(response.headers.get('x-edge-cache'), 'MISS')
  })

  test('com a API da versão em baixo serve a última versão conhecida e só volta a perguntar passados 5 s', async () => {
    await get('/api/categorias')
    expireFreshVersion()
    changeApi({ '/catalogo/version': () => ({ status: 503, data: {} }) })

    const first = await get('/api/categorias')
    const second = await get('/api/categorias')

    assert.equal(first.headers.get('x-edge-cache'), 'HIT')
    assert.equal(second.headers.get('x-edge-cache'), 'HIT')
    assert.equal(versionCalls(), 1) // a segunda não voltou a perguntar
  })

  test('sem versão nenhuma e com a API da versão em baixo, o pedido segue sem cache (BYPASS)', async () => {
    changeApi({ '/catalogo/version': () => ({ status: 503, data: {} }) })

    const response = await get('/api/categorias')

    assert.equal(response.status, 200)
    assert.equal(response.headers.get('x-edge-cache'), 'BYPASS')
  })
})
