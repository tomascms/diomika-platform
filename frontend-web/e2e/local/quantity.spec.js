// @ts-check
// Quantidade com campo numérico (auditoria: BR-03, FE-08, RP-12).
//
// Antes era uma lista com 500 opções (12 → 6000). Agora é um campo numérico com − e +: escreve-se a quantidade,
// e um valor que não é múltiplo do passo é corrigido, por excesso, com um aviso. O banner de cookies não aparece
// (escolha já feita), senão tapava os botões.
import { test, expect } from '@playwright/test'
import { mockApi } from './helpers.js'

const cartLine = (overrides = {}) => ({
  ean: '5606044506574',
  numero_cor: 12,
  quantidade: 12,
  modeloNome: 'Foglia',
  dimensoes: '35x50',
  corNome: 'Azul Ciano',
  carrinhoStep: 12,
  carrinhoMin: 12,
  ...overrides,
})

/** @param {import('@playwright/test').Page} page */
async function setup(page, cart = null) {
  await mockApi(page)
  await page.addInitScript(
    ([stored]) => {
      localStorage.setItem('diomika_cookie_consent', 'rejected')
      if (stored) localStorage.setItem('diomika_cart', JSON.stringify(stored))
    },
    [cart],
  )
}

const quantity = (page) => page.getByRole('spinbutton', { name: 'Quantidade' })
const notice = (page) => page.locator('.qty-notice')

test.describe('ficha do produto', () => {
  test.beforeEach(async ({ page }) => {
    await setup(page)
    await page.goto('/categoria/almofada/foglia')
  })

  test('é um campo numérico com mínimo, passo e máximo, e explica a regra (já não há uma lista de 500 opções)', async ({
    page,
  }) => {
    const field = quantity(page)

    await expect(field).toHaveValue('12')
    await expect(field).toHaveAttribute('type', 'number')
    await expect(field).toHaveAttribute('inputmode', 'numeric')
    await expect(field).toHaveAttribute('min', '12')
    await expect(field).toHaveAttribute('step', '12')
    await expect(field).toHaveAttribute('max', '6000')
    await expect(page.locator('.buy-box select')).toHaveCount(0)
    await expect(page.locator('.qty-hint')).toHaveText('Em múltiplos de 12 un., de 12 a 6000 un.')
    await expect(notice(page)).toHaveCount(0)
  })

  test('− e + andam um passo de cada vez e param no mínimo e no máximo', async ({ page }) => {
    const field = quantity(page)
    const less = page.getByRole('button', { name: 'Diminuir quantidade' })
    const more = page.getByRole('button', { name: 'Aumentar quantidade' })

    await expect(less).toBeDisabled() // já está no mínimo
    await more.click()
    await expect(field).toHaveValue('24')
    await more.click()
    await expect(field).toHaveValue('36')
    await less.click()
    await expect(field).toHaveValue('24')
    await less.click()
    await expect(field).toHaveValue('12')
    await expect(less).toBeDisabled()

    await field.fill('5988')
    await field.press('Tab')
    await expect(field).toHaveValue('5988')
    await more.click()
    await expect(field).toHaveValue('6000')
    await expect(more).toBeDisabled()
    await expect(less).toBeEnabled()
    await expect(notice(page)).toHaveCount(0)
  })

  test('escrever directamente: 240 fica 240 e é o que se junta ao pedido', async ({ page }) => {
    await quantity(page).fill('240')
    // Sem sair do campo: o clique no botão confirma o valor (o campo perde o foco antes do clique).
    await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()

    await expect(page.locator('.added-msg')).toContainText('240 un. adicionadas ao pedido.')
    await expect(notice(page)).toHaveCount(0)
    await page.getByRole('button', { name: 'Ver pedido' }).click()
    await expect(page.getByRole('spinbutton', { name: 'Quantidade de Foglia' })).toHaveValue('240')
  })

  test('escreve-se tecla a tecla sem saltar a meio: «2», «24» e «240» não são corrigidos até sair do campo', async ({
    page,
  }) => {
    const field = quantity(page)
    await field.fill('')
    await field.pressSequentially('240')

    await expect(field).toHaveValue('240')
    await expect(notice(page)).toHaveCount(0)
    await field.press('Tab')
    await expect(field).toHaveValue('240')
    await expect(notice(page)).toHaveCount(0)
  })

  test('um múltiplo inválido sobe ao seguinte, com aviso, e é essa a quantidade que se junta', async ({ page }) => {
    const field = quantity(page)
    await field.fill('100')
    await field.press('Tab')

    await expect(field).toHaveValue('108')
    await expect(notice(page)).toHaveText('Quantidade ajustada de 100 para 108 un.: vendemos em múltiplos de 12.')
    await expect(notice(page)).toHaveAttribute('role', 'status')
    await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()
    await expect(page.locator('.added-msg')).toContainText('108 un. adicionadas ao pedido.')
  })

  test('abaixo do mínimo dá o mínimo e acima do máximo dá o máximo, com o motivo', async ({ page }) => {
    const field = quantity(page)

    await field.fill('5')
    await field.press('Tab')
    await expect(field).toHaveValue('12')
    await expect(notice(page)).toHaveText('Quantidade ajustada de 5 para 12 un.: o mínimo é 12 un.')

    await field.fill('7000')
    await field.press('Enter')
    await expect(field).toHaveValue('6000')
    await expect(notice(page)).toHaveText('Quantidade ajustada de 7000 para 6000 un.: o máximo por pedido é 6000 un.')

    // O aviso desaparece quando a quantidade passa a estar certa.
    await field.fill('120')
    await field.press('Tab')
    await expect(field).toHaveValue('120')
    await expect(notice(page)).toHaveCount(0)
  })

  test('campo vazio volta à quantidade anterior em vez de saltar para o mínimo', async ({ page }) => {
    const field = quantity(page)
    await field.fill('240')
    await field.press('Tab')
    await field.fill('')
    await field.press('Tab')

    await expect(field).toHaveValue('240')
    await expect(notice(page)).toHaveCount(0)
  })
})

test.describe('ficha do produto com outro passo', () => {
  test('toalhas de mesa vendem-se de 6 em 6', async ({ page }) => {
    await setup(page)
    await page.goto('/categoria/toalhas-mesa/toalha-natal')
    const field = quantity(page)

    await expect(field).toHaveValue('6')
    await expect(page.locator('.qty-hint')).toHaveText('Em múltiplos de 6 un., de 6 a 6000 un.')
    await page.getByRole('button', { name: 'Aumentar quantidade' }).click()
    await expect(field).toHaveValue('12')
    await field.fill('7')
    await field.press('Tab')
    await expect(field).toHaveValue('12')
    await expect(notice(page)).toHaveText('Quantidade ajustada de 7 para 12 un.: vendemos em múltiplos de 6.')
  })
})

test.describe('pedido', () => {
  test('cada linha tem o seu campo, com nome próprio; corrigir uma quantidade grava-a e actualiza o total', async ({
    page,
  }) => {
    await setup(page, [
      cartLine(),
      cartLine({ ean: '5606044506598', numero_cor: 13, modeloNome: 'Agate', carrinhoStep: 6, carrinhoMin: 6, quantidade: 6 }),
    ])
    await page.goto('/carrinho')

    const foglia = page.getByRole('spinbutton', { name: 'Quantidade de Foglia' })
    const agate = page.getByRole('spinbutton', { name: 'Quantidade de Agate' })
    await expect(foglia).toHaveValue('12')
    await expect(agate).toHaveValue('6')
    await expect(page.locator('.lines-head .badge-pill')).toHaveText('2 artigos · 18 un.')

    await foglia.fill('30')
    await foglia.press('Tab')
    await expect(foglia).toHaveValue('36')
    await expect(page.locator('.qty-notice')).toHaveText(
      'Quantidade ajustada de 30 para 36 un.: vendemos em múltiplos de 12.',
    )
    await expect(page.locator('.lines-head .badge-pill')).toHaveText('2 artigos · 42 un.')
    const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('diomika_cart') || '[]'))
    expect(stored.map((/** @type {{ quantidade: number }} */ l) => l.quantidade)).toEqual([36, 6])

    // O passo da outra linha é 6: o + dela soma 6.
    await page.getByRole('button', { name: 'Aumentar quantidade' }).nth(1).click()
    await expect(agate).toHaveValue('12')
    await expect(page.locator('.lines-head .badge-pill')).toHaveText('2 artigos · 48 un.')
  })

  for (const width of [375, 320]) {
    test(`o campo de quantidade cabe no ecrã de ${width} px, sem scroll horizontal`, async ({ page }) => {
      await page.setViewportSize({ width, height: 812 })
      await setup(page, [cartLine({ quantidade: 6000 }), cartLine({ ean: '5606044506598', quantidade: 6000, modeloNome: 'Agate' })])
      await page.goto('/carrinho')
      await expect(page.getByRole('spinbutton', { name: 'Quantidade de Agate' })).toBeVisible()

      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
      expect(overflow).toBeLessThanOrEqual(0)
    })
  }

  test('na impressão o campo some e a quantidade de cada linha sai em texto', async ({ page }) => {
    await setup(page, [cartLine({ quantidade: 240 })])
    await page.goto('/carrinho')
    const printed = page.locator('.line-qty-print')

    await expect(printed).toBeHidden()
    await expect(page.locator('.line-qty')).toBeVisible()
    await page.emulateMedia({ media: 'print' })
    await expect(printed).toBeVisible()
    await expect(printed).toHaveText('240 un.')
    await expect(page.locator('.line-qty')).toBeHidden()
    // Só as linhas do pedido saem no papel: sem cabeçalho do site, sem formulário e sem botões.
    await expect(page.locator('.print-area')).toBeVisible()
    await expect(page.locator('.app-header')).toBeHidden()
    await expect(page.locator('.form-section')).toBeHidden()
    await expect(page.locator('.print-btn')).toBeHidden()
  })
})
