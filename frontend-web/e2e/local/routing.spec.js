// @ts-check
// Categorias vazias, rotas novas, 404 e separador antigo (auditoria: FE-05, RP-03, SEO-04, RP-04, FE-12, SEO-06,
// BR-01, FE-04, A11Y-12).
//
// O `vite preview` responde ao que não conhece com a loja e HTTP 200, como se o Pages tivesse um fallback; o HTTP 404 dos
// endereços inventados e a abertura de um modelo publicado depois do build são das Functions (functions/_middleware.js),
// testadas em Node (functions-test/). Aqui vê-se o que o visitante vê: a loja sem as categorias vazias, a página 404 da
// loja e a página 404 estática, com a CSP de produção.
import { readFileSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import { fixture, mockApi } from './helpers.js'

const ROBOTS = 'meta[name="robots"]'
const WITH_MODELS = ['Almofada', 'Assento', 'Material de Cozinha', 'Óculos', 'Protetor de Colchão', 'Toalhas de Mesa']

// A CSP que o site tem em produção (public/_headers.production, a mesma de functions/_middleware.js). Sem
// `upgrade-insecure-requests`: não muda o que bloqueia e o `vite preview` é http.
const PRODUCTION_CSP = /Content-Security-Policy:\s*(.+)/
  .exec(readFileSync(new URL('../../public/_headers.production', import.meta.url), 'utf8'))[1]
  .replace(/;?\s*upgrade-insecure-requests/, '')
  .trim()

test.beforeEach(async ({ page }) => {
  await mockApi(page)
  await page.addInitScript(() => localStorage.setItem('diomika_cookie_consent', 'rejected'))
})

/** Uma página estática (public/) servida com a CSP de produção; devolve o que a CSP bloqueou. */
async function openUnderCsp(page, url) {
  const violations = []
  page.on('console', (message) => {
    if (/Content Security Policy|Refused to/i.test(message.text())) violations.push(message.text())
  })
  await page.route(`**${url}`, async (route) => {
    const response = await route.fetch()
    await route.fulfill({
      response,
      headers: { ...response.headers(), 'content-security-policy': PRODUCTION_CSP },
    })
  })
  await page.goto(url)
  return violations
}

test.describe('as categorias sem modelos não aparecem (FE-05, RP-03, SEO-04)', () => {
  test('em /categorias só se listam as que têm modelos', async ({ page }) => {
    await page.goto('/categorias')

    const names = page.locator('.grid .tile-name')
    await expect(names).toHaveCount(WITH_MODELS.length)
    expect(await names.allInnerTexts()).toEqual(WITH_MODELS)
  })

  test('nem o início as destaca: os seis mosaicos são de categorias com modelos', async ({ page }) => {
    await page.goto('/')

    const tiles = page.locator('main .cat-grid').getByRole('link')
    await expect(tiles).toHaveCount(6)
    const names = (await tiles.allInnerTexts()).map((text) => text.trim())
    for (const name of names) expect(WITH_MODELS).toContain(name)
  })

  test('com uma API que ainda não dá a contagem, mostram-se todas (não se sabe o que está vazio)', async ({ page }) => {
    const antiga = (await fixture('categorias')).map(({ modelos_visiveis: _contagem, ...categoria }) => categoria)
    await page.route('**/api/categorias', (route) => route.fulfill({ json: antiga }))
    await page.goto('/categorias')

    await expect(page.locator('.grid .tile-name')).toHaveCount(9)
  })

  test('o link directo de uma categoria vazia abre, diz que não há modelos e pede aos motores de busca que não a guardem', async ({
    page,
  }) => {
    await page.goto('/categoria/guarda-chuvas')

    await expect(page.getByRole('heading', { name: 'Ainda não há modelos nesta categoria' })).toBeVisible()
    await expect(page.locator(ROBOTS)).toHaveAttribute('content', 'noindex')

    // Ao seguir para uma categoria com modelos, a marca sai.
    await page.locator('.empty').getByRole('link', { name: 'Ver catálogo' }).click()
    await page.locator('.grid .tile-name', { hasText: 'Almofada' }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Almofada' })).toBeVisible()
    await expect(page.locator(ROBOTS)).toHaveCount(0)
  })

  test('uma categoria com modelos é indexável', async ({ page }) => {
    await page.goto('/categoria/almofada')

    await expect(page.locator('.grid .card')).toHaveCount(2)
    await expect(page.locator(ROBOTS)).toHaveCount(0)
  })
})

test.describe('os filtros só oferecem o que leva a algum modelo (RP-03)', () => {
  const CATEGORIES = [
    { slug: 'almofada', tipo: 'almofada', id: '4bba6298-b2d8-4d80-9303-49118f2bb29c' },
    { slug: 'material-cozinha', tipo: 'material_cozinha', id: '1b6f633e-3ade-4984-939f-32fecb7867af' },
    { slug: 'oculos', tipo: 'oculo', id: 'cc02e9a8-978d-423f-b38b-e6bc3c0f43fb' },
    { slug: 'toalhas-mesa', tipo: 'toalha_mesa', id: '6496fab1-a7f0-413d-985f-64306a153ed0' },
  ]

  for (const { slug, tipo, id } of CATEGORIES) {
    test(`${slug}: cada filtro lista só as opções com modelos`, async ({ page }) => {
      const meta = await fixture('catalogo/meta')
      const config = [...meta.catalog_types, ...meta.aggregated_categories].find((entry) => entry.tipo === tipo)
      const models = await fixture(`catalogo/${tipo}/modelos-catalogo/${id}`)
      // Calculado à parte, a partir dos dados: as opções do filtro que algum modelo tem.
      const expected = (config.storefront_filters || []).map((filter) =>
        filter.options.filter((option) => models.some((model) => model[filter.field] === option)).map((option) => filter.labels[option]),
      )

      await page.goto(`/categoria/${slug}`)
      await expect(page.locator('.grid .card').first()).toBeVisible()

      const filters = page.locator('.toolbar .tool', { has: page.locator('select') }).filter({ hasNot: page.locator('option[value="az"]') })
      const shown = []
      for (const select of await filters.locator('select').all()) {
        shown.push((await select.locator('option:not([value=""])').allInnerTexts()).map((text) => text.trim()))
      }
      expect(shown).toEqual(expected.filter((options) => options.length))
    })
  }

  test('Material de Cozinha não oferece «Panos de cozinha»: a loja não tem nenhum', async ({ page }) => {
    await page.goto('/categoria/material-cozinha')
    await expect(page.locator('.grid .card').first()).toBeVisible()

    const options = page.getByLabel('Subcategoria').locator('option')
    await expect(options).toHaveText(['Todos', 'Aventais', 'Luvas', 'Pegas'])
  })
})

test.describe('um modelo publicado depois do build (RP-04, FE-04, SEO-06)', () => {
  test('abre por link directo: não há página gerada para ele e a loja abre-o a partir da API', async ({ page }) => {
    // No Pages, functions/_middleware.js serve a loja a este endereço (functions-test/middleware.test.js); aqui o
    // `vite preview` faz o mesmo, e vê-se que a loja mostra um modelo que nenhum ficheiro do build conhece.
    const foglia = await fixture('catalogo/almofada/modelo-detalhe/slug/almofada/foglia')
    const novo = { ...foglia, id: '9d6b0f0a-8f65-4a41-a5de-2d3f6d9a1c11', nome: 'Almofada Nova', slug: 'almofada-nova' }
    await page.route('**/api/catalogo/almofada/modelo-detalhe/slug/almofada/almofada-nova', (route) =>
      route.fulfill({ json: novo }),
    )

    await page.goto('/categoria/almofada/almofada-nova')

    await expect(page.getByRole('heading', { level: 1, name: 'Almofada Nova' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Adicionar ao pedido' })).toBeVisible()
    await expect(page.locator(ROBOTS)).toHaveCount(0)
  })
})

test.describe('endereços que não existem (BR-01, FE-04, A11Y-12)', () => {
  test('/qualquer: a página 404 da loja, com o cabeçalho, o rodapé e sem indexar', async ({ page }) => {
    await page.goto('/qualquer')

    await expect(page.getByRole('heading', { level: 1, name: 'Página não encontrada' })).toBeVisible()
    await expect(page.locator('header .logo-link')).toBeVisible()
    await expect(page.locator('main a', { hasText: 'Voltar ao início' })).toBeVisible()
    await expect(page.locator('.app-footer')).toContainText('DIOMIKA INTERNACIONAL, UNIPESSOAL, LDA')
    await expect(page.locator(ROBOTS)).toHaveAttribute('content', 'noindex')

    await page.locator('main a', { hasText: 'Voltar ao início' }).click()
    await expect(page.getByRole('heading', { level: 1, name: /Têxteis para o lar/ })).toBeVisible()
    await expect(page.locator(ROBOTS)).toHaveCount(0)
  })

  test('/categoria/nao-existe: «já não está disponível», com saída para o catálogo e sem indexar', async ({ page }) => {
    await page.goto('/categoria/nao-existe')

    await expect(page.getByRole('heading', { name: 'Esta categoria já não está disponível' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Ver o catálogo' })).toBeVisible()
    await expect(page.locator(ROBOTS)).toHaveAttribute('content', 'noindex')
  })

  test('um modelo que já não existe: o mesmo, e o modelo que existe é indexável', async ({ page }) => {
    await page.goto('/categoria/almofada/nao-existe')
    await expect(page.getByRole('heading', { name: 'Este produto já não está disponível' })).toBeVisible()
    await expect(page.locator(ROBOTS)).toHaveAttribute('content', 'noindex')

    await page.goto('/categoria/almofada/agate')
    await expect(page.getByRole('heading', { level: 1, name: 'Agate' })).toBeVisible()
    await expect(page.locator(ROBOTS)).toHaveCount(0)
  })

  test('404.html (a que o Pages serve com HTTP 404) tem estilos, <main>, ligações de ajuda e a identificação do prestador, mesmo com a CSP de produção', async ({
    page,
  }) => {
    const violations = await openUnderCsp(page, '/404.html')

    // Sem o CSS (a CSP bloqueava o <style>) o 404 ficava com 16 px e em Times.
    await expect(page.locator('.code')).toHaveCSS('font-size', '64px')
    await expect(page.locator('.btn-primary')).toHaveCSS('background-color', 'rgb(38, 98, 152)')
    const family = await page.locator('h1').evaluate((element) => getComputedStyle(element).fontFamily)
    expect(family).not.toMatch(/times/i)

    await expect(page.locator('main')).toBeVisible()
    await expect(page.getByRole('heading', { level: 1, name: 'Página não encontrada' })).toBeVisible()
    await expect(page.getByRole('navigation', { name: 'Principal' }).getByRole('link')).toHaveText([
      'Catálogo',
      'Pesquisar',
      'Sobre nós',
      'Contacto',
      'Pedido de orçamento',
    ])
    for (const [name, href] of [
      ['Voltar ao início', '/'],
      ['Ver o catálogo', '/categorias'],
      ['Contacto', '/contacto'],
    ]) {
      await expect(page.locator('main').getByRole('link', { name, exact: true })).toHaveAttribute('href', href)
    }
    await expect(page.locator('main').getByRole('link', { name: 'WhatsApp' })).toHaveAttribute('href', /^https:\/\/wa\.me\/351935745663\?text=/)
    await expect(page.locator('footer address')).toContainText('DIOMIKA INTERNACIONAL, UNIPESSOAL, LDA')
    await expect(page.locator('footer address')).toContainText('NIPC 508 651 557')
    await expect(page.locator('footer address')).toContainText('Rua da Quintã, n.º 89')
    expect(violations).toEqual([])

    // «Saltar para o conteúdo» cai no <main>.
    await page.keyboard.press('Tab')
    await expect(page.getByRole('link', { name: 'Saltar para o conteúdo' })).toBeFocused()
  })

  test('404.html no telemóvel: sem barra horizontal e com os botões a toda a largura', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await openUnderCsp(page, '/404.html')

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(0)
    const button = await page.locator('main .btn-primary').boundingBox()
    expect(button?.width).toBeGreaterThan(250)
  })

  test('status.html: o CSS e o script são ficheiros, por isso a página funciona com a CSP de produção, e identifica o prestador', async ({
    page,
  }) => {
    // Os pedidos que a página de estado faz aos serviços (fora de localhost, respondidos aqui).
    await page.route('https://api.diomika.com/**', (route) =>
      route.fulfill({ status: 200, body: 'online', headers: { 'access-control-allow-origin': '*' } }),
    )
    await openUnderCsp(page, '/status.html')

    await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(243, 245, 247)')
    // Com o <script> dentro do HTML a CSP bloqueava-o e a lista ficava vazia.
    await expect(page.locator('#card-api .pill')).toHaveText('Operacional')
    await expect(page.locator('#card-api-ready .pill')).toHaveText('Operacional')
    await expect(page.locator('#card-site .detail')).not.toHaveText('A verificar…')
    await expect(page.locator('footer address')).toContainText('DIOMIKA INTERNACIONAL, UNIPESSOAL, LDA')
  })

  test('maintenance.html: abre sozinha, com a identificação do prestador', async ({ page }) => {
    await page.goto('/maintenance.html')

    await expect(page.getByRole('heading', { level: 1, name: 'Diomika' })).toBeVisible()
    await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(255, 255, 255)')
    await expect(page.locator('footer address')).toContainText('NIPC 508 651 557')
    await expect(page.locator('footer address')).toContainText('Rua da Quintã, n.º 89')
  })
})

test.describe('separador aberto antes de um deploy (FE-12)', () => {
  const ABOUT_CHUNK = /\/assets\/AboutView-[\w-]+\.js$/

  test('o ficheiro da página já não existe: a loja recarrega-se sozinha na página que se queria abrir', async ({ page }) => {
    let requests = 0
    await page.route(ABOUT_CHUNK, (route) =>
      requests++ === 0 ? route.fulfill({ status: 404, body: 'Not Found' }) : route.continue(),
    )
    await page.goto('/')
    await expect(page.locator('main .cat-grid')).toBeVisible()

    await page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Sobre nós' }).click()

    // Antes nada acontecia: ficava no início, com um erro na consola, até se recarregar à mão. O endereço fica limpo:
    // a marca de «recarregada agora» (que impede um ciclo) sai assim que a página nova arranca.
    await expect(page).toHaveURL(/\/sobre$/)
    await expect(page.getByRole('heading', { level: 1, name: /Têxteis para o lar, de Caldas das Taipas/ })).toBeVisible()
    expect(requests).toBeGreaterThanOrEqual(2)
  })

  test('se o ficheiro continuar em falta depois de recarregar, não recarrega em ciclo', async ({ page }) => {
    // Só os pedidos do documento: as mudanças de página da própria loja (history.pushState) não são carregamentos.
    let loads = 0
    page.on('request', (request) => {
      if (request.isNavigationRequest() && request.frame() === page.mainFrame()) loads++
    })
    await page.route(ABOUT_CHUNK, (route) => route.fulfill({ status: 404, body: 'Not Found' }))
    await page.goto('/')
    await expect(page.locator('main .cat-grid')).toBeVisible()

    await page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Sobre nós' }).click()
    await expect(page).toHaveURL(/\/sobre$/)
    // Passa tempo para um segundo recarregamento aparecer, se houvesse.
    await page.waitForTimeout(2500)

    expect(loads).toBe(2) // o início e o único recarregamento
  })
})
