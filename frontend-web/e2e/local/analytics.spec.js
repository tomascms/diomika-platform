// @ts-check
// Medição (auditoria: RP-10, PERF-06): os passos do funil (juntar ao pedido, pesquisar, WhatsApp, enviar o pedido) e os
// tempos reais de carregamento (web vitals) só se medem com consentimento. Sem ele, nem um pedido ao PostHog: nem sequer
// se descarrega o código dele. O PostHog do harness leva uma chave falsa (playwright.config.js); `trackPosthogEvents`
// (helpers.js) responde-lhe e descodifica o que a loja lhe envia.
import { test, expect } from '@playwright/test'
import { CONSENT_KEY, CONSENT_VERSION } from '../../src/lib/consent.js'
import { fixture, mockApi, trackPosthogEvents } from './helpers.js'

const PEDIDO_ID = '3f2a9c1b-6d4e-4f10-9a77-0c5d2e8b1a34'
const BANNER = { name: 'Consentimento de cookies' }
const accepted = () => JSON.stringify({ state: 'accepted', version: CONSENT_VERSION, date: new Date().toISOString() })

/**
 * @param {import('@playwright/test').Page} page
 * @param {'accepted' | 'rejected' | 'asked'} choice a escolha que a pessoa já fez; `asked`: ainda não fez nenhuma (o banner pergunta)
 */
async function setup(page, choice) {
  await mockApi(page)
  const posthog = await trackPosthogEvents(page)
  // Escrita a cada página: serve para a escolha de partida, não para depois de a pessoa mudar de ideias.
  if (choice !== 'asked') {
    await page.addInitScript(
      ([key, value]) => localStorage.setItem(key, value),
      [CONSENT_KEY, choice === 'accepted' ? accepted() : 'rejected'],
    )
  }
  // O PostHog (código da loja, carregado só com consentimento) não é pedido sem ele.
  /** @type {string[]} */
  const chunks = []
  page.on('request', (request) => {
    if (/\/assets\/posthog-[\w-]+\.js$/.test(new URL(request.url()).pathname)) chunks.push(request.url())
  })
  return { ...posthog, chunks }
}

/** O botão do WhatsApp abriria o wa.me: a loja conta o clique, e aqui a ligação não se segue. */
const keepWhatsAppLinksOnPage = (page) =>
  page.addInitScript(() =>
    document.addEventListener(
      'click',
      (event) => {
        if (event.composedPath().some((el) => el.matches?.('a[href^="https://wa.me/"]'))) event.preventDefault()
      },
      true,
    ),
  )

async function hitsFor(file) {
  const model = await fixture(file)
  return [{ model, category: model.categories, cover_path: '', _tipo_catalogo: model._tipo_catalogo }]
}

/** Os passos do funil, um a um. */
const steps = {
  async addToQuote(page) {
    await page.goto('/categoria/almofada/agate')
    await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()
    await expect(page.getByRole('status').filter({ hasText: 'adicionadas ao pedido' })).toBeVisible()
  },
  async search(page, hits, { measured = false } = {}) {
    await page.route((url) => url.pathname === '/api/catalogo/search', (route) => route.fulfill({ json: hits }))
    await page.goto('/pesquisa')
    // Com consentimento o PostHog arranca depois da página (carrega-se à parte): escreve-se quando já mede.
    if (measured) await page.waitForFunction(() => Boolean(window.__diomikaPosthog))
    await page.getByPlaceholder('Ex.: almofada, 45x45, 5606044…').fill('almofda')
    await expect(page.getByRole('heading', { name: 'Categorias' })).toBeVisible()
    await expect(page.locator('.result-card')).toHaveCount(hits.length)
  },
  async whatsApp(page) {
    await keepWhatsAppLinksOnPage(page)
    await page.goto('/sobre')
    await page.locator('a.whatsapp-fab').click()
    await page.getByRole('main').getByRole('link', { name: 'WhatsApp' }).first().click()
  },
  async submitQuote(page) {
    await page.route(
      (url) => url.hostname === 'challenges.cloudflare.com' && url.pathname === '/turnstile/v0/api.js',
      (route) =>
        route.fulfill({
          contentType: 'text/javascript',
          body: "window.turnstile = { render: (el, options) => { options.callback('token-e2e'); return 'e2e' }, reset() {}, remove() {} }",
        }),
    )
    await page.route(
      (url) => url.pathname === '/api/orcamentos',
      (route) => route.fulfill({ json: { status: 'success', id: PEDIDO_ID } }),
    )
    await page.addInitScript(() =>
      localStorage.setItem(
        'diomika_cart',
        JSON.stringify([
          { ean: '5606044000001', numero_cor: 1, quantidade: 12, modeloNome: 'Modelo 1', dimensoes: '45x45', corNome: 'Azul', carrinho_step: 6, carrinho_min: 6 },
          { ean: '5606044000002', numero_cor: 1, quantidade: 24, modeloNome: 'Modelo 2', dimensoes: '45x45', corNome: 'Azul', carrinho_step: 6, carrinho_min: 6 },
        ]),
      ),
    )
    await page.goto('/carrinho')
    await page.getByLabel('Nome').fill('Ana Silva')
    await page.getByLabel('Email').fill('ana@example.com')
    await page.getByRole('button', { name: 'Enviar pedido de orçamento' }).click()
    await expect(page.getByText('Pedido enviado com sucesso.')).toBeVisible()
  },
}

const named = (events, name) => events.filter((entry) => entry.event === name)

test.describe('com consentimento', () => {
  test('juntar ao pedido: add_to_quote, com o artigo e a quantidade', async ({ page }) => {
    const { events } = await setup(page, 'accepted')
    await steps.addToQuote(page)

    await expect.poll(() => named(events, 'add_to_quote').length).toBe(1)
    expect(named(events, 'add_to_quote')[0].properties).toMatchObject({ model: 'Agate', quantity: 12, ean: '5606044199011' })
  })

  test('pesquisar: search, com o que se escreveu e quantos resultados houve', async ({ page }) => {
    const { events } = await setup(page, 'accepted')
    await steps.search(page, await hitsFor('catalogo/almofada/modelo-detalhe/slug/almofada/agate'), { measured: true })

    await expect.poll(() => named(events, 'search').length).toBe(1)
    expect(named(events, 'search')[0].properties).toMatchObject({ term: 'almofda', results: 1 })
  })

  test('WhatsApp: whatsapp_click do botão flutuante e das ligações, com a página', async ({ page }) => {
    const { events } = await setup(page, 'accepted')
    await steps.whatsApp(page)

    await expect.poll(() => named(events, 'whatsapp_click').length).toBe(2)
    expect(named(events, 'whatsapp_click').map((entry) => entry.properties)).toEqual([
      expect.objectContaining({ page: '/sobre', button: 'flutuante' }),
      expect.objectContaining({ page: '/sobre', button: 'ligação' }),
    ])
  })

  test('enviar o pedido: quote_submitted, com a referência que a pessoa vê', async ({ page }) => {
    const { events } = await setup(page, 'accepted')
    await steps.submitQuote(page)

    await expect.poll(() => named(events, 'quote_submitted').length).toBe(1)
    expect(named(events, 'quote_submitted')[0].properties).toMatchObject({
      reference: PEDIDO_ID.slice(0, 8),
      items_count: 2,
      total_units: 36,
    })
  })

  test('web vitals: o PostHog envia os tempos reais de carregamento ($web_vitals)', async ({ page }) => {
    const { events } = await setup(page, 'accepted')
    await page.goto('/')
    await expect(page.locator('main .cat-grid')).toBeVisible()

    // O PostHog junta as medidas e envia-as ao fim de ~5 s, ou quando a página passa para segundo plano.
    await expect
      .poll(() => named(events, '$web_vitals').length, { timeout: 20_000, intervals: [500] })
      .toBeGreaterThan(0)
    const vitals = named(events, '$web_vitals')[0].properties
    expect(Object.keys(vitals).some((key) => /^\$web_vitals_(FCP|LCP|CLS|INP)_value$/.test(key))).toBe(true)
  })
})

test.describe('sem consentimento (recusado)', () => {
  test('nenhum passo do funil nem os web vitals chegam ao PostHog, e o código dele nem se descarrega', async ({ page }) => {
    const { requests, events, chunks } = await setup(page, 'rejected')

    await steps.addToQuote(page)
    await steps.search(page, await hitsFor('catalogo/almofada/modelo-detalhe/slug/almofada/agate'))
    await steps.whatsApp(page)
    await steps.submitQuote(page)
    // Mais do que os ~5 s que o PostHog esperaria para enviar os web vitals.
    await page.waitForTimeout(6_000)

    expect(requests).toEqual([])
    expect(events).toEqual([])
    expect(chunks).toEqual([])
  })

  test('mudar de ideias: depois de retirar o consentimento, o funil já não se mede', async ({ page }) => {
    const { requests, events } = await setup(page, 'asked')
    await keepWhatsAppLinksOnPage(page)
    await page.goto('/sobre')
    await page.getByRole('region', BANNER).getByRole('button', { name: 'Aceitar' }).click()
    await expect.poll(() => requests.length).toBeGreaterThan(0) // aceitou: o PostHog mede
    await page.locator('.app-footer').getByRole('button', { name: 'Preferências de cookies' }).click()
    await page.getByRole('region', BANNER).getByRole('button', { name: 'Recusar' }).click()
    await expect(page.getByRole('region', BANNER)).toBeHidden()
    const before = requests.length
    const eventsBefore = events.length

    await steps.addToQuote(page)
    await page.goto('/sobre')
    await page.locator('a.whatsapp-fab').click()
    await page.waitForTimeout(1_000)

    expect(requests.length).toBe(before)
    expect(events.length).toBe(eventsBefore)
  })
})
