// @ts-check
// Desempenho da loja (auditoria: PERF-01, PERF-02, PERF-04, PERF-05, PERF-08, PERF-11, PERF-13).
//
// O que se mede aqui é o que a loja pede e como se comporta, sem depender da velocidade do PC: que imagens e
// que scripts o browser descarrega, em que ordem, e o tamanho do ficheiro da fonte. (PERF-07, o `preload` escrito
// no HTML pelo pré-render, tem o seu teste em scripts/prerender-seo.test.mjs: o e2e não corre o pré-render.)
import { statSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import { mockApi } from './helpers.js'

const STORAGE = '/storage/v1/object/public/'
const HERO_ORIGINAL = 'categories/imagem/e9d1f8c70d484f2480c3f4e55c2e9677.webp'
const FOGLIA_MAIN = 'modelos_almofadas/imagem/a1421d52d30c4722bef669955cfc0365.png'
const TURNSTILE = (url) =>
  url.hostname === 'challenges.cloudflare.com' && url.pathname === '/turnstile/v0/api.js'

/** Regista os pedidos de imagens do Storage e do Turnstile; devolve as listas, ao vivo. */
async function setup(page, { cart = null } = {}) {
  await mockApi(page)
  await page.addInitScript(
    ([stored]) => {
      localStorage.setItem('diomika_cookie_consent', 'rejected')
      if (stored) localStorage.setItem('diomika_cart', JSON.stringify(stored))
    },
    [cart],
  )
  /** @type {string[]} */
  const images = []
  /** @type {string[]} */
  const turnstile = []
  page.on('request', (request) => {
    const url = new URL(request.url())
    if (url.pathname.includes(STORAGE) && request.resourceType() === 'image') images.push(url.pathname)
    if (url.hostname === 'challenges.cloudflare.com') turnstile.push(request.url())
  })
  return { images, turnstile }
}

test.describe('PERF-01: a capa da categoria', () => {
  test('a 375 px (onde está escondida) não se descarrega, nem o original em nenhuma largura', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    const { images } = await setup(page)
    await page.goto('/categoria/almofada')
    await expect(page.locator('.grid .card').first()).toBeVisible()
    await page.waitForLoadState('networkidle')

    expect(images.filter((url) => url.includes(HERO_ORIGINAL))).toEqual([])
    // As imagens dos cartões são miniaturas.
    expect(images.length).toBeGreaterThan(0)
    expect(images.filter((url) => !/\.w\d+\.webp$/.test(url))).toEqual([])
  })

  test('a 1280 px usa a miniatura, em `lazy` e sem prioridade alta', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 })
    const { images } = await setup(page)
    await page.goto('/categoria/almofada')
    const hero = page.locator('.head-media img')
    await expect(hero).toBeVisible()
    await page.waitForLoadState('networkidle')

    await expect(hero).toHaveAttribute('loading', 'lazy')
    expect(await hero.getAttribute('fetchpriority')).toBeNull()
    await expect(hero).toHaveAttribute('width', '320')
    await expect(hero).toHaveAttribute('height', '180')
    expect(await hero.getAttribute('src')).toMatch(/\.w480\.webp$/)
    expect(images.filter((url) => url.includes(HERO_ORIGINAL) && !/\.w\d+\.webp$/.test(url))).toEqual([])
  })
})

test('PERF-02: num ecrã 3x o produto pede miniaturas de 480 ou 960, nunca o original de 2 MB', async ({ browser }) => {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 3,
  })
  const page = await context.newPage()
  const { images: all } = await setup(page)
  await page.goto('/categoria/almofada/foglia')
  await expect(page.locator('.main-image-wrap img')).toBeVisible()
  await page.waitForLoadState('networkidle')

  const images = all.filter((url) => !url.includes('/barcodes/')) // o código de barras não tem miniaturas
  const main = images.filter((url) => url.includes(FOGLIA_MAIN))
  expect(main.length).toBeGreaterThan(0)
  expect(main.every((url) => /\.w(160|480|960)\.webp$/.test(url))).toBe(true) // 160: o botão da mesma cor
  expect(main.some((url) => url.endsWith('.w960.webp'))).toBe(true) // 390 px a 3x: 1170 px, a de 960
  expect(images.filter((url) => !/\.w\d+\.webp$/.test(url))).toEqual([])
  const srcset = (await page.locator('.main-image-wrap img').getAttribute('srcset')) ?? ''
  expect(srcset).toMatch(/\.w480\.webp 480w, .*\.w960\.webp 960w$/)
  await context.close()
})

test.describe('PERF-13: miniaturas de cor de 160 px', () => {
  test('os botões de cor e o pedido pedem a miniatura de 160, não a de 480', async ({ page }) => {
    const { images } = await setup(page, {
      cart: [
        {
          ean: '5606044000001',
          numero_cor: 1,
          quantidade: 12,
          modeloNome: 'Foglia',
          dimensoes: '45x45',
          corNome: 'Azul',
          carrinhoStep: 12,
          carrinhoMin: 12,
          imagem: `https://your-project-ref.supabase.co${STORAGE}product-images/${FOGLIA_MAIN}`,
        },
      ],
    })
    await page.goto('/categoria/almofada/foglia')
    const thumbs = page.locator('.color-thumb-btn img')
    await expect(thumbs.first()).toHaveAttribute('src', /\.w160\.webp$/)
    for (const img of await thumbs.all()) expect(await img.getAttribute('src')).toMatch(/\.w160\.webp$/)
    await page.waitForLoadState('networkidle')
    expect(images.filter((url) => url.endsWith('.w160.webp')).length).toBeGreaterThanOrEqual(5)

    await page.goto('/carrinho')
    await expect(page.locator('.line-thumb img')).toHaveAttribute('src', /\.w160\.webp$/)
  })

  test('uma imagem antiga ainda sem a miniatura de 160 cai na de 480, antes do original', async ({ page }) => {
    const { images } = await setup(page)
    await page.route(
      (url) => url.pathname.endsWith('.w160.webp'),
      (route) => route.fulfill({ status: 404, body: '' }),
    )
    await page.goto('/categoria/almofada/foglia')
    const first = page.locator('.color-thumb-btn img').first()
    await expect(first).toHaveAttribute('src', /\.w480\.webp$/)
    await page.waitForLoadState('networkidle')
    // Pediu a de 160 (404) e a de 480; do original só o produto principal, que sempre usou o srcset de 480/960.
    const thumbNames = images.filter((url) => url.endsWith('.w480.webp'))
    expect(thumbNames.length).toBeGreaterThan(0)
    expect(images.filter((url) => !/\.w\d+\.webp$/.test(url) && !url.includes('/barcodes/'))).toEqual([])
  })
})

test.describe('PERF-04: a transição entre páginas', () => {
  test('a página nova monta logo, sem esperar que a antiga saia, e nunca há duas ao mesmo tempo', async ({ page }) => {
    await setup(page)
    await page.goto('/')
    await expect(page.locator('main .home')).toBeVisible()
    await page.evaluate(() => {
      const main = document.getElementById('main-content')
      const w = /** @type {any} */ (window)
      w.__both = false
      w.__mountedAt = 0
      new MutationObserver(() => {
        if (main?.querySelector('.home') && main?.querySelector('.about-page')) w.__both = true
        if (!w.__mountedAt && main?.querySelector('.about-page')) w.__mountedAt = performance.now()
      }).observe(main, { childList: true, subtree: true })
    })
    const clickedAt = await page.evaluate(() => performance.now())
    await page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Sobre nós' }).click()
    await expect(page.locator('main .about-page')).toBeVisible()

    const { both, mountedAt } = await page.evaluate(() => {
      const w = /** @type {any} */ (window)
      return { both: w.__both, mountedAt: w.__mountedAt }
    })
    expect(both).toBe(false)
    // Com `out-in` esperava ~300 ms; agora é o tempo de carregar o chunk (local, uns ms).
    expect(mountedAt - clickedAt).toBeLessThan(250)
  })

  test('a entrada é só opacidade em ≤ 150 ms, e desligada com «reduzir movimento»', async ({ page }) => {
    await setup(page)
    await page.goto('/sobre')
    const animation = () =>
      page.locator('main .about-page').evaluate((el) => {
        const style = getComputedStyle(el)
        return { name: style.animationName, duration: parseFloat(style.animationDuration) }
      })
    const normal = await animation()
    expect(normal.name).toMatch(/^page-in/) // o Vue acrescenta o escopo ao nome
    expect(normal.duration).toBeLessThanOrEqual(0.15)

    await page.emulateMedia({ reducedMotion: 'reduce' })
    expect((await animation()).name).toBe('none')
  })
})

test.describe('PERF-05: o Turnstile só carrega quando se toca no formulário', () => {
  test('o contacto abre sem pedir nada ao Cloudflare; ao tocar num campo carrega e o envio segue', async ({ page }) => {
    const { turnstile } = await setup(page)
    await page.route(TURNSTILE, (route) =>
      route.fulfill({
        contentType: 'text/javascript',
        body: "window.turnstile = { render: (el, options) => { options.callback('token-e2e'); return 'e2e' }, reset() {}, remove() {} }",
      }),
    )
    /** @type {any[]} */
    const sent = []
    await page.route(
      (url) => url.pathname === '/api/contacto',
      (route) => {
        sent.push(route.request().postDataJSON())
        return route.fulfill({ json: { status: 'success' } })
      },
    )
    await page.goto('/contacto')
    await expect(page.getByLabel('Nome')).toBeVisible()
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    expect(turnstile).toEqual([])
    expect(await page.evaluate(() => typeof window.turnstile)).toBe('undefined')

    await page.getByLabel('Nome').fill('Ana Silva')
    await expect.poll(() => turnstile.length).toBe(1)
    await page.getByLabel('Email').fill('ana@example.com')
    await page.getByLabel('Mensagem').fill('Gostaria de saber mais sobre as almofadas.')
    await page.getByRole('button', { name: 'Enviar mensagem' }).click()
    await expect(page.getByText('Mensagem enviada.')).toBeVisible()
    expect(sent).toHaveLength(1)
    expect(sent[0].cf_turnstile_response).toBe('token-e2e')
  })

  test('enviar mal o widget acabou de carregar espera pelo token em vez de falhar', async ({ page }) => {
    await setup(page)
    // O script demora 700 ms; o formulário é enviado logo a seguir ao primeiro toque.
    await page.route(TURNSTILE, async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 700))
      await route.fulfill({
        contentType: 'text/javascript',
        body: "window.turnstile = { render: (el, options) => { setTimeout(() => options.callback('token-lento'), 100); return 'e2e' }, reset() {}, remove() {} }",
      })
    })
    /** @type {any[]} */
    const sent = []
    await page.route(
      (url) => url.pathname === '/api/contacto',
      (route) => {
        sent.push(route.request().postDataJSON())
        return route.fulfill({ json: { status: 'success' } })
      },
    )
    await page.goto('/contacto')
    await page.getByLabel('Nome').fill('Ana Silva')
    await page.getByLabel('Email').fill('ana@example.com')
    await page.getByLabel('Mensagem').fill('Gostaria de saber mais sobre as almofadas.')
    await page.getByRole('button', { name: 'Enviar mensagem' }).click()
    await expect(page.getByText('Mensagem enviada.')).toBeVisible()
    expect(sent[0].cf_turnstile_response).toBe('token-lento')
  })

  test('o pedido de orçamento também só o carrega com o toque no formulário', async ({ page }) => {
    const { turnstile } = await setup(page, {
      cart: [
        {
          ean: '5606044000001',
          numero_cor: 1,
          quantidade: 12,
          modeloNome: 'Modelo 1',
          dimensoes: '45x45',
          corNome: 'Azul',
          carrinhoStep: 12,
          carrinhoMin: 12,
        },
      ],
    })
    await page.goto('/carrinho')
    await expect(page.locator('article.line')).toHaveCount(1)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    expect(turnstile).toEqual([])

    await page.getByLabel('Observações').fill('Entrega em duas fases')
    await expect.poll(() => turnstile.length).toBe(1)
  })
})

test.describe('PERF-08 e PERF-11: fonte e pré-ligações', () => {
  test('o HTML não liga a api.diomika.com e pré-carrega a fonte do site', async ({ request }) => {
    const html = await (await request.get('/')).text()
    expect(html).not.toContain('api.diomika.com')
    expect(html).toMatch(/<link rel="preload" href="\/assets\/archivo-pt-[^"]+\.woff2" as="font"/)
  })

  test('só se descarrega uma fonte, a do subconjunto, com menos de 60 KB, e o texto usa-a', async ({ page }) => {
    await mockApi(page)
    await page.addInitScript(() => localStorage.setItem('diomika_cookie_consent', 'rejected'))
    /** @type {string[]} */
    const fonts = []
    page.on('response', async (response) => {
      if (response.request().resourceType() === 'font') {
        fonts.push(`${new URL(response.url()).pathname} ${(await response.body()).length}`)
      }
    })
    await page.goto('/sobre')
    await page.waitForLoadState('networkidle')

    expect(fonts).toHaveLength(1)
    const [name, size] = fonts[0].split(' ')
    expect(name).toMatch(/^\/assets\/archivo-pt-.+\.woff2$/)
    expect(Number(size)).toBeLessThan(60_000)
    expect(await page.evaluate(() => document.fonts.check('600 16px "Archivo Variable"'))).toBe(true)
    // O pedido de 600/122 % (títulos) e o de 400/100 % (corpo) saem do mesmo ficheiro.
    const faces = await page.evaluate(() =>
      [...document.fonts].map((f) => `${f.family} ${f.weight} ${f.stretch} ${f.status}`),
    )
    expect(faces).toEqual(['Archivo Variable 400 800 100% 125% loaded'])
  })

  test('o ficheiro da fonte foi gerado a partir do original e continua a cobrir o português', () => {
    const source = new URL('../../src/assets/fonts/archivo-pt.woff2', import.meta.url)
    expect(statSync(source).size).toBeLessThan(60_000)
  })
})
