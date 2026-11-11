// @ts-check
// Pesquisa (auditoria: BR-02, FE-06, RP-07).
//
// Quem escreve «almofada» (o nome de uma categoria com 2 modelos) recebia «Sem resultados». A pesquisa dos modelos é da API
// (backend-api/tests/test_catalog_search.py: acentos, maiúsculas, plural, gralhas, cores, medidas, EAN); aqui vê-se o que a
// loja faz com ela: pergunta-lhe o que a pessoa escreveu, sugere as categorias (que a loja já tem em memória) mesmo quando
// a API não devolve nada, tem uma caixa no cabeçalho e diz o que se pode procurar.
import { test, expect } from '@playwright/test'
import { fixture, mockApi } from './helpers.js'

/**
 * A API simulada responde à pesquisa com `hits` e regista o que lhe perguntam.
 * @param {import('@playwright/test').Page} page
 * @param {object[]} hits
 * @returns {Promise<string[]>} as pesquisas (o `q`), ao vivo
 */
async function answerSearchWith(page, hits) {
  /** @type {string[]} */
  const asked = []
  await page.route(
    (url) => url.pathname === '/api/catalogo/search',
    (route) => {
      asked.push(new URL(route.request().url()).searchParams.get('q') ?? '')
      return route.fulfill({ json: hits })
    },
  )
  return asked
}

async function hitFor(file) {
  const model = await fixture(file)
  return { model, category: model.categories, cover_path: '', _tipo_catalogo: model._tipo_catalogo }
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
  await page.addInitScript(() => localStorage.setItem('diomika_cookie_consent', 'rejected'))
})

test.describe('a página de pesquisa', () => {
  test('diz o que se pode procurar, sem o termo técnico «slug»', async ({ page }) => {
    await page.goto('/pesquisa')

    await expect(page.getByPlaceholder('Ex.: almofada, 45x45, 5606044…')).toBeVisible()
    await expect(page.getByText('Pesquise por categoria, nome do modelo, cor, medida ou EAN.')).toBeVisible()
    await expect(page.locator('main')).not.toContainText(/slug/i)
  })

  test('«almofda» (com uma gralha) sugere a categoria Almofada, mesmo que a API não devolva nada', async ({ page }) => {
    const asked = await answerSearchWith(page, [])
    await page.goto('/pesquisa?q=almofda')

    await expect(page.getByRole('heading', { name: 'Sem resultados' })).toBeVisible()
    const suggestion = page.getByRole('region', { name: 'Categorias' }).getByRole('link', { name: /Almofada/ })
    await expect(suggestion).toBeVisible()
    // A API recebe o que a pessoa escreveu, tal e qual: a tolerância a gralhas é dela.
    expect(asked).toEqual(['almofda'])

    await suggestion.click()
    await expect(page).toHaveURL(/\/categoria\/almofada$/)
    await expect(page.getByRole('heading', { level: 1, name: 'Almofada' })).toBeVisible()
  })

  test('maiúsculas, plural e acentos: «ALMOFADAS» e «óculos» encontram a sua categoria', async ({ page }) => {
    await answerSearchWith(page, [])

    await page.goto('/pesquisa?q=ALMOFADAS')
    await expect(page.getByRole('region', { name: 'Categorias' }).getByRole('link', { name: /Almofada/ })).toBeVisible()

    await page.goto('/pesquisa?q=oculos')
    await expect(page.getByRole('region', { name: 'Categorias' }).getByRole('link', { name: /Óculos/ })).toBeVisible()
  })

  test('com resultados, a categoria vem antes dos modelos', async ({ page }) => {
    await answerSearchWith(page, [
      await hitFor('catalogo/almofada/modelo-detalhe/slug/almofada/agate'),
      await hitFor('catalogo/almofada/modelo-detalhe/slug/almofada/foglia'),
    ])
    await page.goto('/pesquisa?q=almofada')

    await expect(page.getByRole('region', { name: 'Categorias' }).getByRole('link', { name: /Almofada/ })).toBeVisible()
    await expect(page.locator('.result-card')).toHaveCount(2)
    const categoryBox = await page.locator('.category-hits').boundingBox()
    const resultsBox = await page.locator('.result-grid').boundingBox()
    expect(categoryBox.y).toBeLessThan(resultsBox.y)
  })

  test('o que não é uma categoria (uma cor, uma medida, um EAN) não sugere nenhuma', async ({ page }) => {
    await answerSearchWith(page, [])
    for (const term of ['azul', '45x45', '5606044199011']) {
      await page.goto(`/pesquisa?q=${term}`)
      await expect(page.getByRole('heading', { name: 'Sem resultados' })).toBeVisible()
      await expect(page.locator('.category-hits')).toHaveCount(0)
    }
  })

  test('uma categoria sem modelos (que a loja esconde) nunca é sugerida', async ({ page }) => {
    await answerSearchWith(page, [])
    await page.goto('/pesquisa?q=guarda-chuva')

    await expect(page.getByRole('heading', { name: 'Sem resultados' })).toBeVisible()
    await expect(page.locator('.category-hits')).toHaveCount(0)
  })
})

test.describe('a caixa de pesquisa do cabeçalho (RP-07)', () => {
  test('em ecrã largo está à vista no cabeçalho, no lugar da ligação «Pesquisar»', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 })
    const asked = await answerSearchWith(page, [])
    await page.goto('/sobre')

    const box = page.locator('header').getByRole('searchbox', { name: 'Pesquisar no catálogo' })
    await expect(box).toBeVisible()
    await expect(page.locator('header .main-nav').getByRole('link', { name: 'Pesquisar' })).toBeHidden()

    await box.fill('almofda')
    await box.press('Enter')

    await expect(page).toHaveURL(/\/pesquisa\?q=almofda$/)
    await expect(page.getByRole('heading', { name: 'Sem resultados' })).toBeVisible()
    // O cabeçalho continua a mostrar o que se procura.
    await expect(box).toHaveValue('almofda')
    expect(asked).toEqual(['almofda'])
  })

  test('o botão com a lupa também pesquisa, e uma caixa vazia leva à página de pesquisa', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 })
    await answerSearchWith(page, [])
    await page.goto('/')

    await page.locator('header').getByRole('button', { name: 'Pesquisar' }).click()
    await expect(page).toHaveURL(/\/pesquisa$/)

    // `header.app-header`: a página de pesquisa tem o seu próprio <header> com outra caixa (a nova página monta logo, PERF-04).
    await page.locator('header.app-header').getByRole('searchbox').fill('azul')
    await page.locator('header.app-header').getByRole('button', { name: 'Pesquisar' }).click()
    await expect(page).toHaveURL(/\/pesquisa\?q=azul$/)
  })

  test('em ecrã médio a caixa não cabe: fica a ligação «Pesquisar» do cabeçalho', async ({ page }) => {
    await page.setViewportSize({ width: 1100, height: 800 })
    await page.goto('/')

    await expect(page.locator('header').getByRole('searchbox')).toBeHidden()
    await page.locator('header .main-nav').getByRole('link', { name: 'Pesquisar' }).click()
    await expect(page).toHaveURL(/\/pesquisa$/)
  })

  test('no telemóvel o cabeçalho fica como estava: pedido e menu, e «Pesquisar» dentro do menu', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/')

    await expect(page.locator('header').getByRole('searchbox')).toBeHidden()
    await page.getByRole('button', { name: 'Abrir menu' }).click()
    await expect(page.locator('header .main-nav').getByRole('link', { name: 'Pesquisar' })).toBeVisible()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(0)
  })

  test('o cabeçalho de 1181 px cabe sem sobreposições nem barra horizontal', async ({ page }) => {
    await page.setViewportSize({ width: 1181, height: 800 })
    await page.goto('/')

    const inner = await page.locator('.header-inner').boundingBox()
    const last = await page.locator('.header-actions .cart-link').boundingBox()
    const nav = await page.locator('.main-nav').boundingBox()
    const search = await page.locator('.header-search').boundingBox()
    expect(search.x).toBeGreaterThanOrEqual(nav.x + nav.width - 1) // a caixa vem depois do menu
    expect(last.x + last.width).toBeLessThanOrEqual(inner.x + inner.width + 1)
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(0)
  })
})
