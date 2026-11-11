import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { collectCatalogue } from './catalogue.js'
import { robotsTxt, sitemapEntries, sitemapXml } from './sitemap.js'
import { STATIC_PAGES } from '../../scripts/static-pages.mjs'

// As respostas reais da API que os testes e2e usam (e2e/local/fixtures): 9 categorias, 3 sem modelos mostráveis, 26 modelos.
const FIXTURES = new URL('../../e2e/local/fixtures/', import.meta.url)
const fixture = (path) =>
  JSON.parse(readFileSync(new URL(`${path.replace(/^\//, '')}.json`, FIXTURES), 'utf8'))
const api = async (path) => fixture(path)

test('collectCatalogue: só as categorias com modelos mostráveis, e esses modelos', async () => {
  const catalogue = await collectCatalogue(api)

  assert.deepEqual(
    catalogue.map((section) => section.slug),
    ['almofada', 'assento', 'material-cozinha', 'oculos', 'protetores-colchao', 'toalhas-mesa'],
  )
  assert.equal(
    catalogue.reduce((total, section) => total + section.models.length, 0),
    26,
  )
  // Guarda-Chuva, Passadeira e Regional estão na API mas não têm nada para mostrar: não entram.
  assert.ok(
    !catalogue.some((section) =>
      ['guarda-chuvas', 'passadeiras', 'regional'].includes(section.slug),
    ),
  )
})

test('collectCatalogue: um modelo sem EAN ou sem cor visível não entra, uma categoria que fica sem modelos também', async () => {
  const almofadas = fixture(
    'catalogo/almofada/modelos-catalogo/4bba6298-b2d8-4d80-9303-49118f2bb29c',
  )
  const [agate, foglia] = almofadas
  const semEan = structuredClone(agate)
  semEan.product_variants.forEach((variant) => (variant.ean = ''))
  const semCor = structuredClone(foglia)
  semCor.modelo_cores.forEach((cor) => (cor.visibilidade = false))

  const onlyBroken = await collectCatalogue(async (path) =>
    path.includes('modelos-catalogo/4bba6298') ? [semEan, semCor] : api(path),
  )
  assert.ok(!onlyBroken.some((section) => section.slug === 'almofada'))

  const oneGood = await collectCatalogue(async (path) =>
    path.includes('modelos-catalogo/4bba6298') ? [semEan, foglia] : api(path),
  )
  assert.deepEqual(
    oneGood.find((section) => section.slug === 'almofada').models.map((model) => model.nome),
    [foglia.nome],
  )
})

test('collectCatalogue: se a API falhar a meio, falha (um mapa do site sem categorias seria pior do que nenhum)', async () => {
  await assert.rejects(
    collectCatalogue(async (path) => {
      if (path.includes('modelos-catalogo/46f8285b')) throw new Error('HTTP 503')
      return api(path)
    }),
    /HTTP 503/,
  )
  await assert.rejects(
    collectCatalogue(async () => Promise.reject(new Error('sem rede'))),
    /sem rede/,
  )
})

test('sitemapEntries: páginas estáticas, depois cada categoria e os seus modelos', async () => {
  const entries = sitemapEntries(STATIC_PAGES, await collectCatalogue(api))
  const paths = entries.map((entry) => entry.path)

  const inSitemap = STATIC_PAGES.filter((page) => page.sitemap !== false).length
  assert.equal(entries.length, inSitemap + 6 + 26)
  assert.equal(new Set(paths).size, paths.length)
  assert.ok(paths.includes('/categoria/almofada'))
  assert.ok(paths.includes('/categoria/almofada/agate'))
  assert.ok(paths.includes('/categoria/material-cozinha/avental-chefe'))
  // As páginas que não se anunciam (carrinho, pedido rápido, catálogo para imprimir) não entram.
  assert.ok(!paths.includes('/carrinho') && !paths.includes('/pedido-rapido'))
  assert.ok(!paths.some((path) => /guarda-chuvas|passadeiras|regional/.test(path)))
  // A categoria vem antes dos seus modelos.
  assert.ok(paths.indexOf('/categoria/almofada') < paths.indexOf('/categoria/almofada/agate'))
})

test('sitemapEntries: lastmod só com data real (a do modelo; a da categoria é a do mais recente)', async () => {
  const catalogue = await collectCatalogue(api)
  const entries = sitemapEntries(STATIC_PAGES, catalogue)
  const byPath = Object.fromEntries(entries.map((entry) => [entry.path, entry]))

  // As páginas estáticas não têm data: a do dia do build dizia que tudo mudava em cada deploy (SEO-11).
  for (const page of STATIC_PAGES.filter((candidate) => candidate.sitemap !== false)) {
    assert.equal(byPath[page.path].lastmod, '', page.path)
  }
  const almofadas = catalogue.find((section) => section.slug === 'almofada').models
  const agate = almofadas.find((model) => model.nome === 'Agate')
  assert.equal(byPath['/categoria/almofada/agate'].lastmod, agate.updated_at.slice(0, 10))
  assert.equal(
    byPath['/categoria/almofada'].lastmod,
    almofadas
      .map((model) => model.updated_at.slice(0, 10))
      .sort()
      .at(-1),
  )

  const sem = sitemapEntries(
    [],
    [{ slug: 'x', models: [{ nome: 'Sem data', updated_at: 'ontem' }, { nome: 'Nulo' }] }],
  )
  assert.deepEqual(
    sem.map((entry) => entry.lastmod),
    ['', '', ''],
  )
})

test('sitemapXml: formato do protocolo, endereços absolutos, lastmod só onde há data, caracteres escapados', () => {
  const xml = sitemapXml('https://www.diomika.com', [
    { path: '/', changefreq: 'weekly', priority: '1.0', lastmod: '' },
    { path: '/categoria/a&b/c', changefreq: 'weekly', priority: '0.7', lastmod: '2026-10-03' },
  ])

  assert.match(
    xml,
    /^<\?xml version="1.0" encoding="UTF-8"\?>\n<urlset xmlns="http:\/\/www.sitemaps.org\/schemas\/sitemap\/0.9">\n/,
  )
  assert.ok(
    xml.includes(
      '<url><loc>https://www.diomika.com/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>',
    ),
  )
  assert.ok(
    xml.includes(
      '<url><loc>https://www.diomika.com/categoria/a&amp;b/c</loc><lastmod>2026-10-03</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>',
    ),
  )
  assert.ok(xml.endsWith('</urlset>\n'))
})

test('robotsTxt: não anuncia o que não se anuncia, não bloqueia o mapa e aponta para ele com o endereço completo', () => {
  const text = robotsTxt('https://www.diomika.com', STATIC_PAGES)

  assert.equal(
    text,
    [
      'User-agent: *',
      'Allow: /',
      'Disallow: /carrinho',
      'Disallow: /pedido-rapido',
      'Disallow: /catalogo-imprimir',
      'Disallow: /api/',
      '',
      'Sitemap: https://www.diomika.com/sitemap.xml',
      '',
    ].join('\n'),
  )
  // O antigo bloqueava `*.xml` (o próprio mapa) e dava o mapa por um endereço relativo (SEO-11).
  assert.doesNotMatch(text, /\*\.xml|\*\.json|Sitemap: \//)
})

test('public/robots.txt, o de reserva, é igual ao que o pré-render escreve', () => {
  const published = readFileSync(
    new URL('../../public/robots.txt', import.meta.url),
    'utf8',
  ).replaceAll('\r\n', '\n')

  assert.equal(published, robotsTxt('https://www.diomika.com', STATIC_PAGES))
})
