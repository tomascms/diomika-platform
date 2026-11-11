// @ts-check
// Acessibilidade WCAG 2.2 AA (auditoria: A11Y-01 a A11Y-06, A11Y-08 a A11Y-11, BR-07).
//
// Um teste por achado. Os contrastes calculam-se aqui, a partir das cores que o browser aplica de facto.
import { test, expect } from '@playwright/test'
import { fixture, mockApi } from './helpers.js'

const MOBILE = { width: 375, height: 812 }
const CONSENT_KEY = 'diomika_cookie_consent'

const cartLine = (n, quantidade = 12) => ({
  ean: `56060440000${String(n).padStart(2, '0')}`,
  numero_cor: 1,
  quantidade,
  modeloNome: `Modelo com um nome comprido para forçar a quebra ${n}`,
  dimensoes: '45x45',
  corNome: 'Azul',
  carrinhoStep: 12,
  carrinhoMin: 12,
})

/**
 * @param {import('@playwright/test').Page} page
 * @param {{ consent?: boolean, cart?: object[] | null }} [options] `consent: false` = primeira visita (com banner)
 */
async function setup(page, { consent = true, cart = null } = {}) {
  await mockApi(page)
  await page.addInitScript(
    ([key, withConsent, stored]) => {
      if (withConsent) localStorage.setItem(key, 'rejected')
      if (stored) localStorage.setItem('diomika_cart', JSON.stringify(stored))
    },
    [CONSENT_KEY, consent, cart],
  )
}

/** Luminância relativa (WCAG) de «rgb(r, g, b)» ou «rgba(...)». */
const luminance = (css) => {
  const [r, g, b] = (css.match(/[\d.]+/g) || []).slice(0, 3).map((v) => {
    const c = Number(v) / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
const contrast = (a, b) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

test.describe('banner de cookies (A11Y-01, BR-07)', () => {
  test('nenhum elemento com foco fica tapado pelo banner, a 375 px, no produto e no contacto', async ({
    page,
  }) => {
    await page.setViewportSize(MOBILE)
    await setup(page, { consent: false })
    for (const url of ['/categoria/almofada/foglia', '/contacto']) {
      await page.goto(url)
      await expect(page.getByRole('region', { name: 'Consentimento de cookies' })).toBeVisible()
      const covered = []
      for (let i = 0; i < 90; i++) {
        await page.keyboard.press('Tab')
        const hidden = await page.evaluate(async () => {
          // O foco rola a página com `scroll-behavior: smooth`: mede-se quando ela pára.
          for (let last = -1, n = 0; n < 20 && last !== scrollY; n++) {
            last = scrollY
            await new Promise((r) => setTimeout(r, 60))
          }
          const el = document.activeElement
          if (!el || el === document.body) return null
          const r = el.getBoundingClientRect()
          if (!r.width || !r.height) return null
          const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)
          if (!top?.closest('.cookie-banner') || el.closest('.cookie-banner')) return null
          return `${el.tagName} ${(el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 30)} tapado pelo banner`
        })
        if (hidden) covered.push(hidden)
      }
      expect(covered, `${url}: foco tapado`).toEqual([])
    }
  })

  test('o banner vem logo a seguir ao skip link, é uma região (não um diálogo) e o Esc recusa', async ({
    page,
  }) => {
    await setup(page, { consent: false })
    await page.goto('/sobre')
    const banner = page.getByRole('region', { name: 'Consentimento de cookies' })
    await expect(banner).toBeVisible()
    await expect(page.getByRole('dialog', { name: 'Consentimento de cookies' })).toHaveCount(0)

    await page.keyboard.press('Tab') // skip link
    await page.keyboard.press('Tab') // primeira ligação do banner: «Cookies»
    await expect(banner.getByRole('link', { name: 'Cookies' })).toBeFocused()

    await page.keyboard.press('Escape')
    await expect(banner).toBeHidden()
    expect(await page.evaluate((key) => localStorage.getItem(key), CONSENT_KEY)).toContain('rejected')
  })

  test('com o banner à vista a página ganha folga por baixo e scroll-padding-bottom; sem ele, nada', async ({
    page,
  }) => {
    await setup(page, { consent: false })
    await page.goto('/sobre')
    const banner = page.getByRole('region', { name: 'Consentimento de cookies' })
    await expect(banner).toBeVisible()
    const height = (await banner.boundingBox())?.height ?? 0
    const padding = () =>
      page.evaluate(() => ({
        scroll: parseFloat(getComputedStyle(document.documentElement).scrollPaddingBottom) || 0,
        body: parseFloat(getComputedStyle(document.body).paddingBottom) || 0,
      }))
    const open = await padding()
    expect(open.scroll).toBeGreaterThanOrEqual(height + 16)
    expect(open.body).toBeGreaterThanOrEqual(height + 16)

    await banner.getByRole('button', { name: 'Recusar' }).click()
    await expect(banner).toBeHidden()
    expect(await padding()).toEqual({ scroll: 0, body: 0 })
  })

  test('a 375 px o banner tapa menos de um quinto do ecrã (BR-07: eram 18 % e pior com o texto maior)', async ({
    page,
  }) => {
    await page.setViewportSize(MOBILE)
    await setup(page, { consent: false })
    await page.goto('/')
    const banner = page.getByRole('region', { name: 'Consentimento de cookies' })
    await expect(banner).toBeVisible()
    await page.waitForTimeout(400) // a entrada acaba
    expect((await banner.boundingBox())?.height ?? 999).toBeLessThanOrEqual(MOBILE.height * 0.2)
  })
})

test('A11Y-02: a lightbox recebe o foco, prende-o, deixa o resto inerte e devolve o foco ao gatilho', async ({
  page,
}) => {
  await setup(page)
  await page.goto('/categoria/almofada/foglia')
  const trigger = page.getByRole('button', { name: 'Ampliar imagem' })
  await trigger.focus()
  await page.keyboard.press('Enter')

  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole('button', { name: 'Fechar' })).toBeFocused()
  expect(await page.evaluate(() => document.getElementById('app')?.hasAttribute('inert'))).toBe(true)

  for (let i = 0; i < 4; i++) {
    await page.keyboard.press('Tab')
    await expect(dialog.getByRole('button', { name: 'Fechar' })).toBeFocused()
  }

  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
  expect(await page.evaluate(() => document.getElementById('app')?.hasAttribute('inert'))).toBe(false)
  await expect(trigger).toBeFocused()
})

test('A11Y-03: só a cor e a medida escolhidas ficam marcadas, com aria-pressed', async ({ page }) => {
  await setup(page)
  await page.goto('/categoria/almofada/foglia')
  const colors = page.locator('.color-thumb-btn')
  await expect(colors.first()).toBeVisible()
  const count = await colors.count()
  expect(count).toBeGreaterThan(1)

  await expect(page.locator('.color-thumb-btn.active')).toHaveCount(1)
  await expect(page.locator('.color-thumb-btn[aria-pressed=true]')).toHaveCount(1)
  await expect(page.locator('.color-thumb-btn[aria-pressed=false]')).toHaveCount(count - 1)
  await expect(colors.first()).toHaveAttribute('aria-pressed', 'true')

  await colors.nth(2).click()
  await expect(colors.nth(2)).toHaveAttribute('aria-pressed', 'true')
  await expect(colors.first()).toHaveAttribute('aria-pressed', 'false')
  await expect(page.locator('.color-thumb-btn.active')).toHaveCount(1)
  // O nome acessível diz a cor (a miniatura em si não tem texto alternativo).
  await expect(colors.nth(2)).toHaveAccessibleName(/^Cor \d+/)

  const chips = page.locator('.picker-chip')
  expect(await chips.count()).toBeGreaterThan(1)
  await expect(page.locator('.picker-chip[aria-pressed=true]')).toHaveCount(1)
  await chips.nth(1).click()
  await expect(chips.nth(1)).toHaveAttribute('aria-pressed', 'true')
  await expect(chips.first()).toHaveAttribute('aria-pressed', 'false')
})

test('A11Y-04: o pedido não rola na horizontal a 320 px', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 })
  await setup(page, { cart: [cartLine(1)] })
  await page.goto('/carrinho')
  await expect(page.locator('article.line')).toHaveCount(1)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320)
  // E o botão «Imprimir / PDF» está inteiro no ecrã.
  const print = await page.getByRole('button', { name: /Imprimir/ }).boundingBox()
  expect((print?.x ?? 0) + (print?.width ?? 999)).toBeLessThanOrEqual(320)
})

test('A11Y-04 (1.4.12): com o espaçamento de texto do WCAG o pedido também não rola na horizontal a 375 px', async ({
  page,
}) => {
  await page.setViewportSize(MOBILE)
  await setup(page, { cart: [cartLine(1), cartLine(2)] })
  await page.goto('/carrinho')
  await expect(page.locator('article.line')).toHaveCount(2)
  await page.addStyleTag({
    content:
      '* { line-height: 1.5 !important; letter-spacing: 0.12em !important; word-spacing: 0.16em !important } p { margin-bottom: 2em !important }',
  })
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375)
})

test('A11Y-05: as ligações dentro de texto têm sublinhado', async ({ page }) => {
  await setup(page, { consent: false })
  await page.goto('/contacto')
  const underlined = (locator) =>
    locator.evaluate((el) => getComputedStyle(el).textDecorationLine.includes('underline'))
  const banner = page.getByRole('region', { name: 'Consentimento de cookies' })
  await expect(banner).toBeVisible()
  expect(await underlined(banner.getByRole('link', { name: 'Privacidade' }))).toBe(true)
  expect(await underlined(page.locator('.privacy-note a').first())).toBe(true)

  await page.goto('/privacidade')
  const links = page.locator('main p a')
  expect(await links.count()).toBeGreaterThan(0)
  for (const link of await links.all()) expect(await underlined(link)).toBe(true)
})

test('A11Y-06: o contador do pedido tem contraste de 4,5:1 e o nome acessível diz quantos artigos', async ({
  page,
}) => {
  await setup(page, { cart: [cartLine(1), cartLine(2)] })
  await page.goto('/')
  const badge = page.locator('header .cart-badge')
  await expect(badge).toHaveText('2')
  const { color, background } = await badge.evaluate((el) => {
    const style = getComputedStyle(el)
    return { color: style.color, background: style.backgroundColor }
  })
  expect(contrast(color, background)).toBeGreaterThanOrEqual(4.5)
  await expect(page.locator('header .cart-link')).toHaveAccessibleName(/2 artigos/)
})

test.describe('mensagens de estado (A11Y-08)', () => {
  test('a região de estado do produto já existe antes de juntar e recebe a mensagem', async ({
    page,
  }) => {
    await setup(page)
    await page.goto('/categoria/almofada/foglia')
    const region = page.locator('[role=status]:has(> .added-msg), [role=status]:empty').first()
    await expect(region).toBeAttached()
    const handle = await region.elementHandle()
    await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()
    await expect(region).toContainText('un. adicionadas ao pedido.')
    // É o mesmo elemento: só o texto mudou.
    expect(await handle?.evaluate((el) => el.isConnected)).toBe(true)
    expect(await handle?.evaluate((el) => el.textContent)).toContain('adicionadas')
  })

  test('a pesquisa anuncia o número de resultados e «Sem resultados»', async ({ page }) => {
    await setup(page)
    const foglia = await fixture('catalogo/almofada/modelo-detalhe/slug/almofada/foglia')
    await page.route(
      (url) => url.pathname === '/api/catalogo/search',
      (route) => {
        const q = new URL(route.request().url()).searchParams.get('q')
        const hits = q === 'foglia' ? [{ model: foglia, category: foglia.categories, cover_path: '' }] : []
        return route.fulfill({ json: hits })
      },
    )
    await page.goto('/pesquisa')
    const status = page.locator('.search-page p[role=status]')
    await expect(status).toBeAttached()
    await expect(status).toHaveText('')

    await page.getByRole('searchbox', { name: 'Pesquisar catálogo' }).fill('foglia')
    await expect(status).toHaveText('1 resultado')
    await page.getByRole('searchbox', { name: 'Pesquisar catálogo' }).fill('zzzzqqqq')
    await expect(status).toHaveText('Sem resultados')
  })
})

test('A11Y-09: o cartão do produto não tem botões dentro da ligação e a imagem não repete o nome', async ({
  page,
}) => {
  await setup(page)
  await page.goto('/categoria/almofada')
  await expect(page.locator('.grid .card').first()).toBeVisible()
  expect(await page.locator('a.card button').count()).toBe(0)
  expect(await page.locator('.card-nav').count()).toBeGreaterThan(0)
  for (const img of await page.locator('a.card img').all()) {
    expect(await img.getAttribute('alt')).toBe('')
  }
  // O nome acessível é o texto do cartão, sem «Cor anterior/seguinte» nem o nome repetido pela imagem.
  const foglia = page.getByRole('link', { name: /Foglia/ }).first()
  await expect(foglia).toHaveAccessibleName(/^\S*\s?Foglia 5 cores$|Foglia 5 cores$/)
  // Os botões continuam a funcionar e ficam sobre a foto.
  const nav = page.locator('.grid > li', { has: page.locator('a.card', { hasText: 'Foglia' }) })
  await nav.hover()
  const next = nav.getByRole('button', { name: 'Cor seguinte' })
  await expect(next).toBeVisible()
  const media = await nav.locator('.card-media').boundingBox()
  const box = await next.boundingBox()
  expect(box && media && box.y > media.y && box.y + box.height <= media.y + media.height).toBe(true)
})

test.describe('foco (A11Y-10)', () => {
  test('Esc no menu móvel devolve o foco ao botão do menu', async ({ page }) => {
    await page.setViewportSize(MOBILE)
    await setup(page)
    await page.goto('/')
    const menu = page.getByRole('button', { name: 'Abrir menu' })
    await menu.click()
    await page.getByRole('link', { name: 'Catálogo' }).first().focus()
    await page.keyboard.press('Escape')
    await expect(page.locator('.main-nav')).toBeHidden()
    await expect(page.getByRole('button', { name: 'Abrir menu' })).toBeFocused()
  })

  test('depois de mudar de página o foco vai para o título da nova', async ({ page }) => {
    await setup(page)
    await page.goto('/')
    await page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Sobre nós' }).click()
    await expect(page).toHaveURL(/\/sobre$/)
    await expect(page.locator('main h1')).toBeFocused()

    await page.getByRole('contentinfo').getByRole('link', { name: 'Contacto', exact: true }).click()
    await expect(page.locator('main h1')).toBeFocused()
  })

  test('escrever na pesquisa (muda só a query) não tira o foco do campo', async ({ page }) => {
    await setup(page)
    await page.goto('/pesquisa')
    const input = page.getByRole('searchbox', { name: 'Pesquisar catálogo' })
    await input.click()
    await input.pressSequentially('almo')
    await page.waitForTimeout(500)
    await expect(input).toBeFocused()
  })
})

test('A11Y-11: o foco do botão do WhatsApp tem contraste de 3:1 com a página', async ({ page }) => {
  await setup(page)
  await page.goto('/sobre')
  const fab = page.locator('.whatsapp-fab')
  await fab.focus()
  await page.keyboard.press('Shift+Tab')
  await page.keyboard.press('Tab')
  await expect(fab).toBeFocused()
  const { outline, width } = await fab.evaluate((el) => {
    const style = getComputedStyle(el)
    return { outline: style.outlineColor, width: parseFloat(style.outlineWidth) }
  })
  expect(width).toBeGreaterThanOrEqual(2)
  expect(contrast(outline, 'rgb(255, 255, 255)')).toBeGreaterThanOrEqual(3)
})
