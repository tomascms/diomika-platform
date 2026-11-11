import { afterEach, beforeEach, describe, test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { onRequest } from '../functions/_middleware.js'
import { installEdge, pagesContext } from './fakes.js'

// A configuração do Pages que decide o que as Functions veem: public/_routes.json (que pedidos as invocam) e
// public/_headers* (o que os ficheiros estáticos levam, sem passar por elas). Só lê ficheiros do repositório.
const PUBLIC = new URL('../public/', import.meta.url)
const read = (name) => readFileSync(new URL(name, PUBLIC), 'utf8').replaceAll('\r\n', '\n')
const routes = JSON.parse(read('_routes.json'))

/** Os caracteres `*` do `_routes.json` valem por qualquer troço do caminho, barras incluídas (documentação do Pages). */
const matches = (pattern, path) =>
  new RegExp(`^${pattern.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replaceAll('*', '.*')}$`).test(path)
const invoked = (path) =>
  routes.include.some((pattern) => matches(pattern, path)) && !routes.exclude.some((pattern) => matches(pattern, path))

describe('_routes.json: menos invocações, as Functions onde fazem falta (PERF-12)', () => {
  test('é válido para o Pages: versão 1, pelo menos uma regra de inclusão, até 100 regras de 100 caracteres, `*` só no fim', () => {
    assert.equal(routes.version, 1)
    assert.ok(routes.include.length >= 1)
    const rules = [...routes.include, ...routes.exclude]
    assert.ok(rules.length <= 100)
    for (const rule of rules) {
      assert.ok(rule.startsWith('/') && rule.length <= 100, rule)
      // A documentação só mostra o `*` no fim de um caminho: não se arrisca outro uso.
      assert.ok(!rule.includes('*') || rule.indexOf('*') === rule.length - 1, rule)
    }
  })

  test('o que as Functions fazem continua a chegar-lhes: /api, o mapa, as páginas, o catálogo novo, os endereços antigos e os bloqueios', () => {
    for (const path of [
      '/api/categorias',
      '/api/catalogo/search',
      '/sitemap.xml',
      '/',
      '/sobre',
      '/categoria/almofada',
      '/categoria/almofada/um-modelo-novo',
      '/produto/5e5f7104-dec3-415c-8996-b16891899c87',
      '/contact',
      '/produtos/almofada',
      '/qualquer', // um endereço que não existe tem de chegar ao 404
      '/.env',
      '/.git/config',
      '/package.json',
      '/src/main.js',
    ]) {
      assert.ok(invoked(path), `${path} já não invoca as Functions`)
    }
  })

  test('os ficheiros estáticos não as invocam (eram ~30 invocações por página vista)', () => {
    for (const path of [
      '/assets/index-D4TJcLPq.js',
      '/assets/archivo-pt-ABC123.woff2',
      '/assets/main-1a2b3c.css',
      '/brand/logo.svg',
      '/favicon.ico',
      '/apple-touch-icon.png',
      '/icon-512.png',
      '/site.webmanifest',
      '/robots.txt',
      '/404.css',
      '/status.js',
    ]) {
      assert.ok(!invoked(path), `${path} invoca as Functions`)
    }
  })

  test('cada ficheiro de public/ está de um lado ou do outro: páginas e mapa invocam, o resto não (um ficheiro novo obriga a decidir)', () => {
    const files = readdirSync(PUBLIC).filter((name) => !name.startsWith('_'))
    for (const name of files) {
      const isDirectory = statSync(new URL(name, PUBLIC)).isDirectory()
      const path = isDirectory ? `/${name}/x` : `/${name}`
      const isPage = name.endsWith('.html') || name === 'sitemap.xml'
      assert.equal(invoked(path), isPage, `${path}: ${isPage ? 'devia invocar as Functions' : 'devia estar em exclude'}`)
    }
  })
})

/** Os cabeçalhos de um bloco `/*` de um `_headers`: nome em minúsculas → valor. */
function headersOf(file) {
  const block = /^\/\*\n((?:[ \t]+.+\n?)+)/m.exec(read(file))[1]
  return Object.fromEntries(
    block
      .split('\n')
      .map((line) => /^\s+([A-Za-z-]+):\s*(.+)$/.exec(line))
      .filter(Boolean)
      .map(([, name, value]) => [name.toLowerCase(), value.trim()]),
  )
}

describe('cabeçalhos de segurança: os ficheiros estáticos levam os mesmos valores que as páginas (PERF-12)', () => {
  let edge
  beforeEach(() => void (edge = installEdge()))
  afterEach(() => edge.restore())

  const middlewareHeaders = async () => {
    const response = await onRequest(pagesContext('https://www.diomika.com/'))
    return [
      'strict-transport-security',
      'x-content-type-options',
      'x-frame-options',
      'x-xss-protection',
      'referrer-policy',
      'permissions-policy',
      'content-security-policy',
    ].map((name) => [name, response.headers.get(name)])
  }

  for (const file of ['_headers', '_headers.production']) {
    test(`${file} diz o mesmo que functions/_middleware.js nos cabeçalhos que ele põe`, async () => {
      const mine = headersOf(file)
      for (const [name, value] of await middlewareHeaders()) {
        assert.ok(value, `o middleware não põe ${name}`)
        assert.equal(mine[name], value, `${file}: ${name}`)
      }
    })
  }

  test('os ficheiros /assets/* continuam com cache longa e imutável', () => {
    for (const file of ['_headers', '_headers.production']) {
      assert.match(read(file), /\/assets\/\*\n\s+Cache-Control: public, max-age=31536000, immutable/)
    }
  })
})
