import { afterEach, beforeEach, describe, test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { onRequest } from '../functions/_middleware.js'
import { NOT_FOUND_HTML, SHELL_HTML, fakeAssets, installEdge, pagesContext } from './fakes.js'

const ALMOFADA_LIST = '/catalogo/almofada/modelos-catalogo/4bba6298-b2d8-4d80-9303-49118f2bb29c'
const fixture = (name) => JSON.parse(readFileSync(new URL(`../e2e/local/fixtures/${name}.json`, import.meta.url), 'utf8'))
const AGATE_ID = fixture(ALMOFADA_LIST.slice(1))[0].id

/** Um modelo publicado depois do último deploy: não existe como ficheiro, só na API. */
const withNewModel = () => {
  const list = fixture(ALMOFADA_LIST.slice(1))
  const novo = structuredClone(list[1])
  Object.assign(novo, { id: '9d6b0f0a-8f65-4a41-a5de-2d3f6d9a1c11', nome: 'Almofada Nova', slug: 'almofada-nova' })
  return { [ALMOFADA_LIST]: () => ({ status: 200, data: [...list, novo] }) }
}

let edge
beforeEach(() => void (edge = installEdge(withNewModel())))
afterEach(() => edge.restore())

const run = async (url, options) => {
  const context = pagesContext(url, options)
  const response = await onRequest(context)
  await context.settled()
  return response
}

describe('domínio canónico e caminhos bloqueados (o que a Function já fazia)', () => {
  test('diomika.com redirecciona para www, com o caminho e a query', async () => {
    const response = await run('https://diomika.com/categoria/almofada?cor=2')

    assert.equal(response.status, 301)
    assert.equal(response.headers.get('location'), 'https://www.diomika.com/categoria/almofada?cor=2')
  })

  test('os endereços antigos redireccionam (301): /contact e /produtos/<categoria>, com a query', async () => {
    for (const [from, to] of [
      ['/contact', '/contacto'],
      ['/contact/', '/contacto'],
      ['/contact?assunto=orcamento', '/contacto?assunto=orcamento'],
      ['/produtos/almofada', '/categoria/almofada'],
      ['/produtos/almofada/', '/categoria/almofada'],
      ['/produtos/material-cozinha?tipo=avental', '/categoria/material-cozinha?tipo=avental'],
    ]) {
      const response = await run(`https://www.diomika.com${from}`)

      assert.equal(response.status, 301, from)
      assert.equal(response.headers.get('location'), `https://www.diomika.com${to}`, from)
    }
  })

  test('e só esses: /contacto, /produtos sozinho e /produtos/a/b não redireccionam', async () => {
    for (const path of ['/contacto', '/contact-us', '/produtos', '/produtos/a/b']) {
      assert.notEqual((await run(`https://www.diomika.com${path}`)).status, 301, path)
    }
  })

  for (const path of ['/.env', '/.env.production', '/.git/config', '/package.json', '/vite.config.js', '/src/main.js', '/backend-api/main.py', '/.github/workflows/ci.yml', '/node_modules/x']) {
    test(`${path} dá 404 sem chegar aos ficheiros`, async () => {
      let reachedAssets = false
      const context = pagesContext(`https://www.diomika.com${path}`)
      context.next = async () => void (reachedAssets = true)

      const response = await onRequest(context)

      assert.equal(response.status, 404)
      assert.equal(response.headers.get('cache-control'), 'no-store')
      assert.equal(await response.text(), 'Not Found')
      assert.equal(reachedAssets, false)
    })
  }

  test('uma página normal passa, com os cabeçalhos de segurança e a CSP de _headers.production', async () => {
    const response = await run('https://www.diomika.com/')

    assert.equal(response.status, 200)
    assert.equal(response.headers.get('x-frame-options'), 'DENY')
    assert.equal(response.headers.get('x-content-type-options'), 'nosniff')
    const headers = readFileSync(new URL('../public/_headers.production', import.meta.url), 'utf8')
    const csp = /Content-Security-Policy:\s*(.+)/.exec(headers)[1].trim()
    assert.equal(response.headers.get('content-security-policy'), csp)
  })
})

describe('páginas do catálogo que o build não gerou (RP-04, FE-04)', () => {
  test('um modelo publicado depois do deploy abre: a loja, com HTTP 200, e o canonical do endereço', async () => {
    const response = await run('https://www.diomika.com/categoria/almofada/almofada-nova?utm_source=whatsapp')

    assert.equal(response.status, 200)
    const html = await response.text()
    assert.match(html, /<div id="app"><\/div>/)
    // O canonical é o do endereço, sem a query (o `/` pré-renderizado traz o da página inicial).
    assert.ok(html.includes('<link rel="canonical" href="https://www.diomika.com/categoria/almofada/almofada-nova">'))
    assert.ok(html.includes('<meta property="og:url" content="https://www.diomika.com/categoria/almofada/almofada-nova">'))
    assert.ok(!html.includes('href="https://www.diomika.com/">'))
    assert.equal(response.headers.get('content-type'), 'text/html; charset=utf-8')
    assert.equal(response.headers.get('cache-control'), 'public, max-age=0, must-revalidate')
    assert.equal(response.headers.get('content-length'), null)
    assert.equal(response.headers.get('x-frame-options'), 'DENY')
  })

  test('um visitante com a página inicial em cache (If-None-Match) recebe a loja, não um 304 sem corpo', async () => {
    const response = await run('https://www.diomika.com/categoria/almofada/almofada-nova', {
      headers: { 'If-None-Match': '"etag-da-pagina-inicial"' },
    })

    assert.equal(response.status, 200)
    assert.match(await response.text(), /<div id="app"><\/div>/)
  })

  test('uma categoria sem modelos existe na API: abre (a loja diz «ainda não há modelos» e marca noindex)', async () => {
    const response = await run('https://www.diomika.com/categoria/guarda-chuvas')

    assert.equal(response.status, 200)
    assert.match(await response.text(), /<div id="app"><\/div>/)
  })

  test('o nome da categoria sem acentos nem maiúsculas também a encontra (como a API)', async () => {
    assert.equal((await run('https://www.diomika.com/categoria/material-de-cozinha')).status, 200)
  })

  test('uma categoria que não existe dá 404 de verdade, com a página 404 estática', async () => {
    const response = await run('https://www.diomika.com/categoria/nao-existe')

    assert.equal(response.status, 404)
    assert.equal(await response.text(), NOT_FOUND_HTML)
  })

  test('um modelo que não existe numa categoria que existe dá 404', async () => {
    assert.equal((await run('https://www.diomika.com/categoria/almofada/nao-existe')).status, 404)
    assert.equal((await run('https://www.diomika.com/categoria/nao-existe/agate')).status, 404)
  })

  test('um modelo que existe só noutra categoria dá 404 aqui', async () => {
    assert.equal((await run('https://www.diomika.com/categoria/assento/agate')).status, 404)
  })

  test('o link antigo /produto/<id> abre se o modelo existe e dá 404 se não', async () => {
    const known = AGATE_ID
    edge.restore()
    edge = installEdge({
      ...withNewModel(),
      [`/catalogo/modelo-detalhe/${known}`]: () => ({ status: 200, data: { id: known } }),
    })

    assert.equal((await run(`https://www.diomika.com/produto/${known}`)).status, 200)
    assert.equal((await run('https://www.diomika.com/produto/5e5f7104-dec3-415c-8996-b16891899c99')).status, 404)
    assert.equal((await run('https://www.diomika.com/produto/nao-e-um-id')).status, 404)
    // Um identificador mal formado nem chega à API.
    assert.ok(!edge.apiCalls.some((call) => call.includes('nao-e-um-id')))
  })

  test('uma página que o build gerou passa sem perguntar nada à API', async () => {
    const assets = fakeAssets({ '/': SHELL_HTML, '/categoria/almofada': '<h1>Almofada</h1>' })

    const response = await run('https://www.diomika.com/categoria/almofada', { assets })

    assert.equal(response.status, 200)
    assert.equal(await response.text(), '<h1>Almofada</h1>')
    assert.deepEqual(edge.apiCalls, [])
  })

  test('ficheiros e outros caminhos em falta continuam a dar o 404 (nada de HTML para um .js que não existe)', async () => {
    for (const path of ['/assets/nao-existe-123.js', '/qualquer', '/categoria', '/categoria/almofada/agate/extra', '/produtos/x/y']) {
      const response = await run(`https://www.diomika.com${path}`)
      assert.equal(response.status, 404, path)
      assert.equal(await response.text(), NOT_FOUND_HTML, path)
    }
    assert.deepEqual(edge.apiCalls, [])
  })

  test('só os GET: um POST ao endereço de um modelo novo não recebe a loja', async () => {
    const response = await run('https://www.diomika.com/categoria/almofada/almofada-nova', { method: 'POST' })

    assert.equal(response.status, 404)
  })

  test('com a API em baixo não se sabe: abre a loja, que mostra o que puder, em vez de um 404 num modelo que existe', async () => {
    edge.fail = true

    const response = await run('https://www.diomika.com/categoria/almofada/almofada-nova')

    assert.equal(response.status, 200)
    assert.match(await response.text(), /<div id="app"><\/div>/)
  })

  test('uma resposta da API que não se percebe também não deita abaixo a página', async () => {
    edge.restore()
    edge = installEdge({ '/categorias': () => ({ status: 200, data: { nao: 'e uma lista' } }) })

    assert.equal((await run('https://www.diomika.com/categoria/almofada')).status, 200)
  })

  test('endereços inventados repetidos não voltam a chegar à API: a lista de categorias vem da cache', async () => {
    await run('https://www.diomika.com/categoria/inventada-1')
    const callsAfterFirst = edge.apiCalls.length

    await run('https://www.diomika.com/categoria/inventada-2')
    await run('https://www.diomika.com/categoria/inventada-3')

    assert.equal(edge.apiCalls.filter((call) => call === '/categorias').length, 1)
    // O pedido da versão do catálogo repete-se no máximo de 5 em 5 s por PoP, não por endereço.
    assert.equal(edge.apiCalls.length, callsAfterFirst)
  })

  test('o erro de um endereço mal codificado dá 404 em vez de rebentar', async () => {
    const response = await run('https://www.diomika.com/categoria/%E0%A4%A')

    assert.equal(response.status, 404)
  })
})
