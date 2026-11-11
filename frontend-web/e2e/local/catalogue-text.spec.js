// @ts-check
// Textos do catálogo (auditoria: FE-03, RP-02, SEO-02, BR-04, BD-01, FE-16, RP-17).
//
// Os dados de produção ainda têm o texto «Sem descrição» em quase todos os modelos (e as fixtures, que são
// cópias reais, também): a loja não o mostra, nem na página nem na meta description, e escreve a descrição a
// partir das especificações. O banner de cookies não aparece (escolha já feita), senão tapava os botões.
import { test, expect } from '@playwright/test'
import { fixture, mockApi, productPages } from './helpers.js'

const META_DESCRIPTIONS = [
  'meta[name="description"]',
  'meta[property="og:description"]',
  'meta[name="twitter:description"]',
]

test.beforeEach(async ({ page }) => {
  await mockApi(page)
  await page.addInitScript(() => localStorage.setItem('diomika_cookie_consent', 'rejected'))
})

test.describe('nenhum modelo mostra «Sem descrição»', () => {
  for (const { url, name, category } of productPages()) {
    test(`${name} (${category})`, async ({ page }) => {
      await page.goto(url)
      await expect(page.getByRole('heading', { level: 1, name, exact: true })).toBeVisible()

      const description = page.locator('.product-desc')
      await expect(description).not.toHaveText(/sem descri/i)
      await expect(description).not.toBeEmpty()

      // O título leva a categoria (antes, depois do JavaScript, perdia-a) e as três metas dizem o mesmo.
      await expect(page).toHaveTitle(`${name} — ${category} | Diomika`)
      const contents = []
      for (const selector of META_DESCRIPTIONS) {
        const content = (await page.locator(selector).getAttribute('content')) ?? ''
        expect(content, selector).not.toMatch(/sem descri/i)
        expect(content.length, selector).toBeGreaterThan(20)
        expect(content.length, selector).toBeLessThanOrEqual(160)
        contents.push(content)
      }
      expect(new Set(contents).size).toBe(1)
    })
  }
})

test.describe('a descrição vem das especificações', () => {
  const GERADAS = [
    [
      '/categoria/almofada/foglia',
      'Tipo: Decorativa. Composição: 100% Poliester. Disponível em 3 medidas (35x50, 45x45 e 60x60 cm) e em 5 cores.',
    ],
    [
      '/categoria/assento/liso',
      'Material do forro: Poliéster. Material do enchimento: Poliuretano. Disponível em 2 alturas (32mm e 45mm).',
    ],
    ['/categoria/material-cozinha/avental-liso?tipo=avental', 'Composição: 100% Poliéster.'],
    ['/categoria/oculos/adulto', 'Tipo: Óculos de sol.'],
    [
      '/categoria/protetores-colchao/protetor-colchao-malha-texturizada',
      'Composição: 100% Poliéster. Disponível em 9 medidas (de 90x200 a 200x200 cm).',
    ],
  ]
  for (const [url, text] of GERADAS) {
    test(url, async ({ page }) => {
      await page.goto(url)
      await expect(page.locator('.product-desc')).toHaveText(text)
      await expect(page.locator('meta[name="description"]')).toHaveAttribute(
        'content',
        `${text} Peça orçamento à Diomika.`,
      )
    })
  }

  test('uma descrição escrita pelo cliente tem prioridade sobre a gerada', async ({ page }) => {
    const path = 'catalogo/almofada/modelo-detalhe/slug/almofada/foglia'
    const foglia = { ...(await fixture(path)), descricao: 'Almofada em veludo, com enchimento de fibra siliconada.' }
    await page.route((url) => url.pathname === `/api/${path}`, (route) => route.fulfill({ json: foglia }))
    await page.goto('/categoria/almofada/foglia')

    await expect(page.locator('.product-desc')).toHaveText(foglia.descricao)
    await expect(page.locator('meta[name="description"]')).toHaveAttribute(
      'content',
      `${foglia.descricao} Peça orçamento à Diomika.`,
    )
  })
})

test.describe('categoria', () => {
  test('o título tem o nome da base de dados («Toalhas de Mesa», não «Toalhas De Mesa») e a meta conta os modelos', async ({
    page,
  }) => {
    await page.goto('/categoria/toalhas-mesa')
    const heading = page.getByRole('heading', { level: 1 })

    await expect(heading).toHaveText('Toalhas de Mesa')
    // `innerText` aplica o `text-transform`: antes dava «Toalhas De Mesa».
    expect(await heading.evaluate((el) => /** @type {HTMLElement} */ (el).innerText)).toBe('Toalhas de Mesa')
    await expect(page).toHaveTitle('Toalhas de Mesa | Diomika')
    await expect(page.locator('meta[name="description"]')).toHaveAttribute(
      'content',
      'Toalhas de Mesa: 5 modelos em várias cores e medidas. Peça orçamento à Diomika — pedido mínimo 500 € + IVA (615 € com IVA a 23 %).',
    )
  })

  test('«Material de Cozinha» também não leva maiúscula em «de»', async ({ page }) => {
    await page.goto('/categoria/material-cozinha')
    const heading = page.getByRole('heading', { level: 1 })

    await expect(heading).toHaveText('Material de Cozinha')
    expect(await heading.evaluate((el) => /** @type {HTMLElement} */ (el).innerText)).toBe('Material de Cozinha')
  })
})

test.describe('ficha do produto', () => {
  test('as especificações não levam notas do backoffice e as medidas vêm por ordem', async ({ page }) => {
    await page.goto('/categoria/toalhas-mesa/protetor-de-mesa')
    const specs = page.locator('.specs-panel')

    // A API guarda as medidas como foram escritas («140x200, 140x250, 140x300, 140x140»).
    await expect(specs.locator('dt')).toHaveText([
      'Composição',
      'Dimensões (comprimento×largura)',
      'Quantidade mínima no pedido',
    ])
    await expect(specs).not.toContainText('igual para todas as cores')
    await expect(specs.locator('.spec-item', { hasText: 'Dimensões' }).locator('dd')).toHaveText(
      '140x140, 140x200, 140x250, 140x300',
    )
  })

  test('sem descrição nem dados, a ficha diz o que fazer, com a ortografia do resto da loja', async ({ page }) => {
    const path = 'catalogo/oculo/modelo-detalhe/slug/oculos/adulto'
    // Sem tipo nem composição não há nada que gerar.
    const oculos = { ...(await fixture(path)), tipo_oculo: null }
    await page.route((url) => url.pathname === `/api/${path}`, (route) => route.fulfill({ json: oculos }))
    await page.goto('/categoria/oculos/adulto')

    await expect(page.locator('.product-desc')).toHaveText(
      'Selecione a cor, indique a quantidade e adicione ao pedido de orçamento.',
    )
    await expect(page.locator('meta[name="description"]')).toHaveAttribute(
      'content',
      'Adulto — óculos. Peça orçamento à Diomika.',
    )
  })
})

test.describe('linhas do pedido', () => {
  for (const [url, meta] of [
    ['/categoria/material-cozinha/avental-liso?tipo=avental', 'Cor 1 (Sortido)'],
    ['/categoria/almofada/foglia', '35x50 cm · Cor 12 (Azul Ciano)'],
    ['/categoria/assento/liso', '32mm · Cor 1 (Sortido)'],
  ]) {
    test(`${url}: sem «Referência» no lugar da medida`, async ({ page }) => {
      await page.goto(url)
      await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()
      await page.getByRole('button', { name: 'Ver pedido' }).click()

      await expect(page.locator('article.line .line-meta')).toHaveText(meta)
    })
  }
})
