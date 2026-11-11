// @ts-check
// Polimento da loja (auditoria: FE-07, FE-17, FE-18, e o contador de RP-17).
//
// O pedido tem de estar à vista no telemóvel, a confirmação de «adicionado» não pode desaparecer sozinha, os
// alvos de toque têm de ter pelo menos 24 px (WCAG 2.5.8), a navegação não rola devagar e o menu fecha ao tocar fora.
// (FE-20, «npm run dev» não usa a API de produção, é testado em vite.config.test.mjs: arranca o servidor.)
import { test, expect } from '@playwright/test'
import { mockApi } from './helpers.js'

const MOBILE = { width: 375, height: 812 }

const cartLine = (n, quantidade = 12) => ({
  ean: `56060440000${String(n).padStart(2, '0')}`,
  numero_cor: 1,
  quantidade,
  modeloNome: `Modelo ${n}`,
  dimensoes: '45x45',
  corNome: 'Azul',
  carrinhoStep: 12,
  carrinhoMin: 12,
})

/**
 * @param {import('@playwright/test').Page} page
 * @param {object[] | null} cart linhas do pedido já feito
 */
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

test.describe('o pedido no cabeçalho (FE-07, RP-17)', () => {
  test('no telemóvel o pedido está à vista com o menu fechado, e o contador conta artigos, não unidades', async ({
    page,
  }) => {
    await page.setViewportSize(MOBILE)
    await setup(page, [cartLine(1, 12), cartLine(2, 60)])
    await page.goto('/')

    const link = page.locator('header .cart-link')
    await expect(page.locator('.main-nav')).toBeHidden() // o menu está fechado
    await expect(link).toBeVisible()
    await expect(link.locator('.cart-badge')).toBeVisible()
    // Duas linhas, 72 unidades: o contador diz 2, o nome diz tudo.
    await expect(link.locator('.cart-badge')).toHaveText('2')
    await expect(link).toHaveAttribute('aria-label', 'Pedido de orçamento: 2 artigos · 72 un.')
    await expect(link).toHaveAttribute('title', 'Pedido de orçamento: 2 artigos · 72 un.')

    await link.click()
    await expect(page).toHaveURL(/\/carrinho$/)
  })

  test('sem artigos não há contador e o nome diz que está vazio', async ({ page }) => {
    await page.setViewportSize(MOBILE)
    await setup(page)
    await page.goto('/')

    const link = page.locator('header .cart-link')
    await expect(link).toBeVisible()
    await expect(link.locator('.cart-badge')).toHaveCount(0)
    await expect(link).toHaveAttribute('aria-label', 'Pedido de orçamento (vazio)')
  })

  test('um só artigo com 12 unidades é «1», no singular', async ({ page }) => {
    await page.setViewportSize(MOBILE)
    await setup(page, [cartLine(1, 12)])
    await page.goto('/')

    await expect(page.locator('header .cart-link .cart-badge')).toHaveText('1')
    await expect(page.locator('header .cart-link')).toHaveAttribute('aria-label', 'Pedido de orçamento: 1 artigo · 12 un.')
  })

  test('no ecrã grande o pedido leva o texto e está fora do menu da mesma maneira', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 })
    await setup(page, [cartLine(1)])
    await page.goto('/')

    const link = page.locator('header .cart-link')
    await expect(link).toContainText('Pedido de orçamento')
    await expect(link.locator('.cart-badge')).toHaveText('1')
    await expect(page.locator('.main-nav .cart-link')).toHaveCount(0)
    await expect(page.locator('.menu-btn')).toBeHidden()
  })

  test('o contador acompanha o pedido sem recarregar a página', async ({ page }) => {
    await page.setViewportSize(MOBILE)
    await setup(page)
    await page.goto('/categoria/almofada/foglia')
    const badge = page.locator('header .cart-link .cart-badge')

    await expect(badge).toHaveCount(0)
    await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()
    await expect(badge).toHaveText('1')
    // Outra cor é outro artigo; a mesma cor e medida só muda a quantidade.
    await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()
    await expect(badge).toHaveText('1')
    await page.locator('.color-thumb-btn').nth(1).click()
    await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()
    await expect(badge).toHaveText('2')
  })

  test('a página do pedido diz «artigos · unidades», sem partir a linha', async ({ page }) => {
    await page.setViewportSize(MOBILE)
    await setup(page, [cartLine(1, 12), cartLine(2, 60)])
    await page.goto('/carrinho')
    const badge = page.locator('.lines-head .badge-pill')

    await expect(badge).toHaveText('2 artigos · 72 un.')
    expect(await badge.evaluate((el) => getComputedStyle(el).whiteSpace)).toBe('nowrap')
    const box = await badge.boundingBox()
    expect(box?.height ?? 99).toBeLessThan(36) // uma linha (antes partia-se em duas)
  })
})

test.describe('a confirmação de «adicionado» (FE-07)', () => {
  test('fica à vista, com a ligação «Ver pedido», e não desaparece sozinha', async ({ page }) => {
    await setup(page)
    await page.goto('/categoria/almofada/foglia')
    await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()
    const message = page.locator('.added-msg')

    await expect(message).toContainText('12 un. adicionadas ao pedido.')
    // A região `status` existe sempre e a mensagem entra nela (A11Y-08).
    await expect(page.locator('[role=status]:has(> .added-msg)')).toBeVisible()
    // Antes sumia aos 2,8 s: quem não olhava não sabia se tinha juntado.
    await page.waitForTimeout(3500)
    await expect(message).toBeVisible()

    await message.getByRole('link', { name: 'Ver pedido' }).click()
    await expect(page).toHaveURL(/\/carrinho$/)
    await expect(page.locator('article.line')).toHaveCount(1)
  })

  test('juntar outra vez actualiza o texto, e outro produto começa sem confirmação', async ({ page }) => {
    await setup(page)
    await page.goto('/categoria/almofada/foglia')
    const message = page.locator('.added-msg')

    await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()
    await expect(message).toContainText('12 un. adicionadas')
    await page.getByRole('button', { name: 'Aumentar quantidade' }).click()
    await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()
    await expect(message).toContainText('24 un. adicionadas')

    await page.goto('/categoria/almofada/agate')
    await expect(page.getByRole('heading', { level: 1, name: 'Agate' })).toBeVisible()
    await expect(message).toHaveCount(0)
  })
})

test.describe('alvos de toque de 24 px ou mais, a 375 px (FE-18, WCAG 2.5.8)', () => {
  const PAGES = ['/', '/categoria/almofada', '/categoria/almofada/foglia', '/carrinho', '/contacto', '/sobre']

  for (const url of PAGES) {
    test(url, async ({ page }) => {
      await page.setViewportSize(MOBILE)
      await setup(page, [cartLine(1)])
      await page.goto(url)
      await expect(page.locator('footer .footer-col a').first()).toBeVisible()

      const targets = [
        '.footer-col a',
        '.footer-col button',
        '.breadcrumb-item a',
        '.logo-link',
        '.cart-link',
        '.menu-btn',
      ]
      const small = []
      for (const selector of targets) {
        for (const element of await page.locator(selector).all()) {
          const box = await element.boundingBox()
          if (!box) continue // fora do ecrã ou escondido
          if (box.width < 24 || box.height < 24) {
            small.push(`${selector} «${(await element.innerText()).trim().slice(0, 30)}» ${Math.round(box.width)}×${Math.round(box.height)}`)
          }
        }
      }
      expect(small, 'alvos com menos de 24 px').toEqual([])
    })
  }

  test('a pesquisa da categoria ocupa a largura toda e já não corta o texto de ajuda', async ({ page }) => {
    await page.setViewportSize(MOBILE)
    await setup(page)
    await page.goto('/categoria/almofada')
    const search = page.getByPlaceholder('Nome do modelo, cor ou EAN')

    await expect(search).toBeVisible()
    const box = await search.boundingBox()
    expect(box?.width ?? 0).toBeGreaterThan(300) // eram 164 px
  })
})

test.describe('navegação (FE-17)', () => {
  test('mudar de página volta ao topo na hora, sem rolar devagar', async ({ page }) => {
    await page.setViewportSize(MOBILE)
    await setup(page)
    await page.goto('/')
    await page.locator('footer').scrollIntoViewIfNeeded()
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(300)

    await page.locator('footer').getByRole('link', { name: 'Informação legal' }).click()
    await expect(page).toHaveURL(/\/termos$/)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    // Com a rolagem animada, 600 ms depois a página ainda ia a meio (y = 433); agora já está no topo.
    await page.waitForTimeout(400)
    expect(await page.evaluate(() => window.scrollY)).toBe(0)
  })

  test('o menu fecha ao tocar fora dele, e com Esc', async ({ page }) => {
    await page.setViewportSize(MOBILE)
    await setup(page)
    await page.goto('/')
    const menu = page.getByRole('button', { name: 'Abrir menu' })
    const nav = page.locator('.main-nav')

    await menu.click()
    await expect(nav).toBeVisible()
    await page.mouse.click(40, 760) // fora do menu e do botão
    await expect(nav).toBeHidden()
    await expect(page.getByRole('button', { name: 'Abrir menu' })).toHaveAttribute('aria-expanded', 'false')

    await page.getByRole('button', { name: 'Abrir menu' }).click()
    await expect(nav).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(nav).toBeHidden()
  })

  test('tocar dentro do menu não o fecha, mas escolher uma página sim', async ({ page }) => {
    await page.setViewportSize(MOBILE)
    await setup(page)
    await page.goto('/')
    const nav = page.locator('.main-nav')

    await page.getByRole('button', { name: 'Abrir menu' }).click()
    await nav.click({ position: { x: 5, y: 5 } })
    await expect(nav).toBeVisible()
    await nav.getByRole('link', { name: 'Contacto' }).click()
    await expect(page).toHaveURL(/\/contacto$/)
    await expect(nav).toBeHidden()
  })
})
