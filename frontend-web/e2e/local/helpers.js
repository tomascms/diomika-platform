// @ts-check
// Harness e2e local (projecto `local` de playwright.config.js).
//
// `mockApi(page)` isola o teste da rede:
//  - `/api/**` em localhost responde com as fixtures (ou 404), nunca chega ao proxy do preview;
//  - qualquer outro pedido http(s) para fora de localhost é abortado e reprova o teste;
//  - fotos para fora de localhost (Storage) levam uma imagem vazia, para a página se compor;
//  - o script do Turnstile (o carrinho e o contacto pedem-no) é simulado: define `window.turnstile`
//    sem fazer nada, não chama o `callback` e portanto nunca dá um token.
// Regista as rotas no contexto (cobre também os separadores abertos pela página). Uma rota
// registada depois, com `page.route(...)`, tem prioridade: é assim que um teste simula um erro,
// um POST ou um serviço externo (PostHog), ou um Turnstile que dá token.
//
// Fixtures: respostas reais de `GET https://www.diomika.com/api/...` (só GET, sem autenticação),
// capturadas a 2026-10-29 e guardadas com JSON indentado. Os tokens JWT (já expirados) dos URLs
// assinados do Storage, que a API devolve nos códigos de barras, foram trocados por `expirado`.
// Única mão da captura: `categorias.json` leva `modelos_visiveis`, o n.º de modelos que a loja mostra em cada categoria
// (a API passou a dá-lo para a loja esconder as vazias, FE-05; a captura é anterior). Sai das listas de modelos daqui.
// Cada uma está no caminho do pedido sem `/api/` nem query: `/api/catalogo/meta` →
// fixtures/catalogo/meta.json. Para acrescentar uma, basta criar o ficheiro. Sem ficheiro o
// pedido leva 404, como um recurso que não existe. A query é ignorada. Só o GET lê fixtures:
// qualquer outro método (um POST de formulário) leva 404 até o teste registar a sua rota.
import { Buffer } from 'node:buffer'
import { readdirSync, readFileSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { gunzipSync } from 'node:zlib'
import { expect } from '@playwright/test'

const FIXTURES = path.join(path.dirname(fileURLToPath(import.meta.url)), 'fixtures')
const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]'])
const EMPTY_IMAGE = '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'

const readFixture = (name) => readFile(path.join(FIXTURES, `${name}.json`), 'utf8')

/** Fixture já lida: `await fixture('categorias')`, `await fixture('catalogo/meta')`. */
export const fixture = async (name) => JSON.parse(await readFixture(name))

/**
 * Uma página de produto por cada modelo que as fixtures cobrem (um ficheiro em
 * fixtures/catalogo/<tipo>/modelo-detalhe/slug/<categoria>/<modelo>.json), para os testes passarem por todos.
 * O material de cozinha junta vários tipos numa categoria: o endereço leva `?tipo=`, como o da loja.
 * `file` é o nome da fixture (para `fixture(file)`).
 * @returns {{ url: string, name: string, category: string, tipo: string, file: string }[]}
 */
export function productPages() {
  const root = path.join(FIXTURES, 'catalogo')
  return readdirSync(root, { recursive: true, encoding: 'utf8' })
    .map((file) => file.split(path.sep).join('/').match(/^([^/]+)\/modelo-detalhe\/slug\/([^/]+)\/([^/]+)\.json$/))
    .filter(Boolean)
    .map(([file, tipo, categorySlug, modelSlug]) => {
      const model = JSON.parse(readFileSync(path.join(root, file), 'utf8'))
      const query = categorySlug === 'material-cozinha' ? `?tipo=${tipo}` : ''
      return {
        url: `/categoria/${categorySlug}/${modelSlug}${query}`,
        name: model.nome,
        category: model.categories.nome,
        tipo,
        file: `catalogo/${file.replace(/\.json$/, '')}`,
      }
    })
}

/** @param {import('@playwright/test').Page} page */
export async function mockApi(page) {
  const context = page.context()
  /** @type {string[]} */
  const blocked = []

  await context.route(
    (url) => url.protocol.startsWith('http') && !LOCAL_HOSTS.has(url.hostname),
    async (route) => {
      const request = route.request()
      if (request.resourceType() === 'image') {
        await route.fulfill({ contentType: 'image/svg+xml', body: EMPTY_IMAGE }).catch(() => {})
        return
      }
      blocked.push(`${request.method()} ${request.url()}`)
      await route.abort('blockedbyclient').catch(() => {})
      try {
        // Soft: reprova o teste sem lançar, a página continua a correr com o pedido falhado.
        expect.soft(blocked, 'Pedidos para fora de localhost (abortados)').toEqual([])
      } catch {
        // O teste já acabou (pedido tardio ao fechar a página): nada a reprovar.
      }
    },
  )

  // Registada depois do bloqueio geral, por isso é esta que responde ao script do Turnstile.
  await context.route(
    (url) =>
      url.hostname === 'challenges.cloudflare.com' && url.pathname === '/turnstile/v0/api.js',
    async (route) => {
      await route
        .fulfill({
          contentType: 'text/javascript',
          body: 'window.turnstile = { render: () => "e2e", reset() {}, remove() {} }',
        })
        .catch(() => {})
    },
  )

  await context.route(
    (url) => LOCAL_HOSTS.has(url.hostname) && url.pathname.startsWith('/api/'),
    async (route) => {
      const request = route.request()
      const { pathname } = new URL(request.url())
      /** @type {Parameters<import('@playwright/test').Route['fulfill']>[0]} */
      let response = {
        status: 404,
        json: { detail: `e2e: sem fixture para ${request.method()} ${pathname}` },
      }
      if (request.method() === 'GET') {
        try {
          const body = await readFixture(pathname.slice('/api/'.length))
          response = { status: 200, contentType: 'application/json', body }
        } catch (error) {
          // Só «não existe» é 404; um erro de leitura não se disfarça de recurso em falta.
          if (error.code !== 'ENOENT') {
            response = {
              status: 500,
              json: { detail: `e2e: erro a ler a fixture de ${pathname}: ${error.message}` },
            }
          }
        }
      }
      await route.fulfill(response).catch(() => {})
    },
  )
}

const isPosthog = (url) => /(^|\.)posthog\.com$/.test(new URL(url).hostname)

/**
 * PostHog dos testes: responde-lhe com 200 vazio (o `mockApi` aborta tudo o que sai de localhost e reprova o
 * teste) e devolve, ao vivo, os pedidos que lhe chegam, como «POST /e/».
 * O PostHog descarta os eventos de browsers que parecem robôs (`navigator.webdriver`, a marca «HeadlessChrome»
 * de `userAgentData`) e o Playwright é um deles: sem estes dois retoques o teste via 0 pedidos mesmo com o
 * código errado. Por isso um teste que afirma «0 pedidos» mostra antes que, com consentimento, há pedidos.
 * @param {import('@playwright/test').Page} page
 */
export async function trackPosthog(page) {
  /** @type {string[]} */
  const requests = []
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false })
    Object.defineProperty(navigator, 'userAgentData', { get: () => undefined })
  })
  page.on('request', (request) => {
    if (isPosthog(request.url())) {
      requests.push(`${request.method()} ${new URL(request.url()).pathname}`)
    }
  })
  await page.route(
    (url) => isPosthog(url.href),
    (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  )
  return requests
}

/**
 * Os eventos do PostHog que o corpo de um pedido leva: `{ event, properties }`. O PostHog manda-os em gzip
 * («compression=gzip-js»), em texto ou em `data=<base64>`, dentro de `batch` (um evento por pedido, com
 * `request_batching: false`).
 * @param {Buffer | null} buffer
 * @returns {{ event: string, properties: Record<string, any> }[]}
 */
function decodePosthogBody(buffer) {
  if (!buffer) return []
  for (const read of [() => gunzipSync(buffer).toString('utf8'), () => buffer.toString('utf8')]) {
    try {
      let text = read()
      if (text.startsWith('data=')) {
        text = Buffer.from(decodeURIComponent(text.slice(5)), 'base64').toString('utf8')
      }
      const json = JSON.parse(text)
      // `{ api_key, batch: [eventos] }`, uma lista de eventos ou um só.
      return (json.batch ?? (Array.isArray(json) ? json : [json])).filter((entry) => entry && entry.event)
    } catch {
      /* tenta a forma seguinte */
    }
  }
  return []
}

/**
 * Como `trackPosthog`, e também os eventos que chegam, descodificados e ao vivo: `events` é uma lista a que se vão
 * juntando `{ event, properties }`; `requests` são os pedidos («POST /e/»).
 * @param {import('@playwright/test').Page} page
 */
export async function trackPosthogEvents(page) {
  const requests = await trackPosthog(page)
  /** @type {{ event: string, properties: Record<string, any> }[]} */
  const events = []
  page.on('request', (request) => {
    if (isPosthog(request.url())) events.push(...decodePosthogBody(request.postDataBuffer()))
  })
  return { requests, events }
}
