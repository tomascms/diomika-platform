// @ts-check
// Informação de produto e sinais de confiança (auditoria: RP-08, RP-09).
//
// A API passa a mandar, para cada família, seis especificações opcionais (cuidados, embalagem, gramagem, origem,
// certificações, prazo: backend-api/models/catalog_attributes.py) e a ficha mostra as que estiverem preenchidas, sem
// código por campo. Aqui a API simulada manda-as como a nova API as manda (o modelo Foglia mais as seis).
import { test, expect } from '@playwright/test'
import { fixture, mockApi } from './helpers.js'

const FOGLIA = 'catalogo/almofada/modelo-detalhe/slug/almofada/foglia'

// Rótulos e tipos iguais aos de CATEGORY_ATTRIBUTE_SCHEMAS (o pytest test_product_info_attributes.py fixa-os).
const INFO_SPECS = [
  { field: 'cuidados', label: 'Cuidados de lavagem', widget: 'string' },
  { field: 'embalagem', label: 'Embalagem (un. por caixa)', widget: 'integer' },
  { field: 'gramagem', label: 'Gramagem (g/m²)', widget: 'integer' },
  { field: 'origem', label: 'País de origem', widget: 'string' },
  { field: 'certificacao', label: 'Certificações', widget: 'string' },
  { field: 'prazo', label: 'Prazo de entrega', widget: 'string' },
].map((spec) => ({ ...spec, enum_labels: {} }))

const FILLED = {
  cuidados: 'Lavar a 30 °C, não usar lixívia',
  embalagem: 12,
  gramagem: 180,
  origem: 'Portugal',
  certificacao: 'OEKO-TEX Standard 100',
  prazo: '5 a 10 dias úteis',
}

/**
 * A Foglia como a nova API a manda: com as seis especificações na lista e os valores que se passarem.
 * @param {import('@playwright/test').Page} page
 * @param {Record<string, unknown>} values
 */
async function serveFoglia(page, values) {
  const foglia = await fixture(FOGLIA)
  const body = { ...foglia, ...values, _storefront: { ...foglia._storefront, specs: [...foglia._storefront.specs, ...INFO_SPECS] } }
  await page.route((url) => url.pathname === `/api/${FOGLIA}`, (route) => route.fulfill({ json: body }))
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
  await page.addInitScript(() => localStorage.setItem('diomika_cookie_consent', 'rejected'))
})

test.describe('especificações', () => {
  test('a ficha mostra todas as que estão preenchidas, a seguir às da família', async ({ page }) => {
    await serveFoglia(page, FILLED)
    await page.goto('/categoria/almofada/foglia')
    const specs = page.locator('.specs-panel')

    await expect(specs.locator('dt')).toHaveText([
      'Composição',
      'Dimensões (comprimento×largura)',
      'Cuidados de lavagem',
      'Embalagem (un. por caixa)',
      'Gramagem (g/m²)',
      'País de origem',
      'Certificações',
      'Prazo de entrega',
      'Quantidade mínima no pedido',
      'Venda',
    ])
    await expect(specs.locator('dd')).toHaveText([
      '100% Poliester',
      '35x50, 45x45, 60x60',
      'Lavar a 30 °C, não usar lixívia',
      '12',
      '180',
      'Portugal',
      'OEKO-TEX Standard 100',
      '5 a 10 dias úteis',
      '12 un. (incrementos de 12)',
      'Vendido em caixas de 12 un.',
    ])
  })

  test('as que ficam por preencher não aparecem, nem linhas vazias', async ({ page }) => {
    await serveFoglia(page, { cuidados: 'Lavar a 30 °C', gramagem: 180, origem: '', prazo: null })
    await page.goto('/categoria/almofada/foglia')

    await expect(page.locator('.specs-panel dt')).toHaveText([
      'Composição',
      'Dimensões (comprimento×largura)',
      'Cuidados de lavagem',
      'Gramagem (g/m²)',
      'Quantidade mínima no pedido',
    ])
  })

  test('«Vendido em caixas» só quando o passo é a caixa: com 24 por caixa e passo 12 fica só a embalagem', async ({
    page,
  }) => {
    await serveFoglia(page, { embalagem: 24 })
    await page.goto('/categoria/almofada/foglia')
    const specs = page.locator('.specs-panel')

    await expect(specs.locator('.spec-item', { hasText: 'Embalagem' }).locator('dd')).toHaveText('24')
    await expect(specs).not.toContainText('Vendido em caixas')
  })

  test('os modelos de hoje, sem estes dados, não ganham linhas vazias', async ({ page }) => {
    await page.goto('/categoria/almofada/foglia')

    await expect(page.locator('.specs-panel dt')).toHaveText([
      'Composição',
      'Dimensões (comprimento×largura)',
      'Quantidade mínima no pedido',
    ])
  })
})

test.describe('identificação e localização', () => {
  test('a ficha não tem o bloco «Quem vende»: a identificação está no rodapé e em «Informação legal»', async ({ page }) => {
    await page.goto('/categoria/almofada/foglia')

    await expect(page.getByRole('heading', { name: 'Quem vende' })).toHaveCount(0)
    await expect(page.locator('main address')).toHaveCount(0)
    await expect(page.getByRole('contentinfo')).toContainText('NIPC 508 651 557')
  })

  for (const width of [375, 320]) {
    test(`a ficha cabe no ecrã de ${width} px, sem scroll horizontal`, async ({ page }) => {
      await page.setViewportSize({ width, height: 812 })
      await page.goto('/categoria/almofada/foglia')
      await expect(page.getByRole('contentinfo')).toBeVisible()

      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
      expect(overflow).toBeLessThanOrEqual(0)
    })
  }

  test('«Sobre nós» diz onde fica a empresa e liga ao mapa, sem mapa incorporado', async ({ page }) => {
    await page.goto('/sobre')
    const where = page.locator('.where-section')

    await expect(where.getByRole('heading', { name: 'Onde estamos' })).toBeVisible()
    await expect(where.locator('address')).toContainText('Rua da Quintã, n.º 89, 4805-116 Caldas das Taipas')
    await expect(where.getByRole('link', { name: 'Ver a morada no mapa' })).toHaveAttribute(
      'href',
      /^https:\/\/www\.google\.com\/maps\/search\/\?api=1&query=/,
    )
    await expect(page.locator('iframe')).toHaveCount(0)
  })
})
