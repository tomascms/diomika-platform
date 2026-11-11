import { afterEach, beforeEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { onRequest } from '../functions/sitemap.xml.js'
import { fakeAssets, installEdge, pagesContext } from './fakes.js'

const ALMOFADA_LIST = '/catalogo/almofada/modelos-catalogo/4bba6298-b2d8-4d80-9303-49118f2bb29c'
const fixture = (name) => JSON.parse(readFileSync(new URL(`../e2e/local/fixtures/${name}.json`, import.meta.url), 'utf8'))
const locs = (xml) => [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((match) => match[1])

const BUILD_SITEMAP = '<?xml version="1.0"?><urlset><url><loc>https://www.diomika.com/</loc></url></urlset>'
const assets = () => fakeAssets({ '/sitemap.xml': BUILD_SITEMAP })

let edge
beforeEach(() => void (edge = installEdge()))
afterEach(() => edge.restore())

const get = async (options = {}) => {
  const context = pagesContext('https://www.diomika.com/sitemap.xml', { assets: assets(), ...options })
  const response = await onRequest(context)
  await context.settled()
  return response
}

test('o mapa sai da API: as páginas estáticas, as categorias com modelos e os 26 modelos', async () => {
  const response = await get()
  const xml = await response.text()

  assert.equal(response.status, 200)
  assert.equal(response.headers.get('content-type'), 'application/xml; charset=utf-8')
  assert.equal(response.headers.get('cache-control'), 'public, max-age=600')
  const urls = locs(xml)
  assert.ok(urls.includes('https://www.diomika.com/'))
  assert.ok(urls.includes('https://www.diomika.com/sobre'))
  assert.ok(urls.includes('https://www.diomika.com/categoria/almofada'))
  assert.ok(urls.includes('https://www.diomika.com/categoria/almofada/agate'))
  assert.equal(urls.filter((url) => /\/categoria\/[^/]+\/[^/]+$/.test(url)).length, 26)
  assert.equal(urls.filter((url) => /\/categoria\/[^/]+$/.test(url)).length, 6)
  // Nem as categorias vazias nem as páginas que não se anunciam.
  assert.ok(!urls.some((url) => /guarda-chuvas|passadeiras|regional|carrinho|pedido-rapido/.test(url)))
  assert.match(xml, /<loc>https:\/\/www\.diomika\.com\/categoria\/almofada\/agate<\/loc><lastmod>2026-10-03<\/lastmod>/)
})

test('um modelo publicado hoje entra no mapa de hoje, sem deploy', async () => {
  const list = fixture(ALMOFADA_LIST.slice(1))
  const novo = { ...structuredClone(list[1]), id: '9d6b0f0a-8f65-4a41-a5de-2d3f6d9a1c11', nome: 'Almofada Nova', slug: 'almofada-nova' }
  edge.restore()
  edge = installEdge({ [ALMOFADA_LIST]: () => ({ status: 200, data: [...list, novo] }) })

  const urls = locs(await (await get()).text())

  assert.ok(urls.includes('https://www.diomika.com/categoria/almofada/almofada-nova'))
})

test('o mapa lista sempre www.diomika.com, venha o pedido de onde vier', async () => {
  const context = pagesContext('https://diomika-loja.pages.dev/sitemap.xml', { assets: assets() })

  const urls = locs(await (await onRequest(context)).text())

  assert.ok(urls.every((url) => url.startsWith('https://www.diomika.com/')))
})

test('com a API em baixo serve o mapa que o build escreveu', async () => {
  edge.fail = true

  const response = await get()

  assert.equal(await response.text(), BUILD_SITEMAP)
})

test('se a API responder mas o catálogo não tiver nada para mostrar, também serve o do build', async () => {
  edge.restore()
  edge = installEdge({ '/categorias': () => ({ status: 200, data: [] }) })

  assert.equal(await (await get()).text(), BUILD_SITEMAP)
})

test('se a lista de uma categoria falhar, não se publica um mapa incompleto', async () => {
  edge.restore()
  edge = installEdge({ [ALMOFADA_LIST]: () => ({ status: 503, data: { detail: 'indisponível' } }) })

  assert.equal(await (await get()).text(), BUILD_SITEMAP)
})

test('só GET e HEAD', async () => {
  const response = await get({ method: 'POST' })

  assert.equal(response.status, 405)
  assert.equal(response.headers.get('allow'), 'GET, HEAD')
})
