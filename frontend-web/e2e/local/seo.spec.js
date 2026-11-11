// @ts-check
// SEO e WhatsApp (auditoria: SEO-05, RP-13): o canonical nunca leva a query, e o botão do WhatsApp, na página de um modelo,
// leva o modelo, a cor e a medida escolhidos, o EAN e o endereço.
import { test, expect } from '@playwright/test'
import { mockApi } from './helpers.js'

const SITE = 'https://www.diomika.com'
const DEFAULT_TEXT = 'Olá! Gostaria de obter mais informações sobre o catálogo Diomika.'

test.beforeEach(async ({ page }) => {
  await mockApi(page)
  await page.addInitScript(() => localStorage.setItem('diomika_cookie_consent', 'rejected'))
})

const canonical = (page) => page.locator('link[rel="canonical"]')
const ogUrl = (page) => page.locator('meta[property="og:url"]')
/** O texto que o botão flutuante leva (o `?text=` da ligação wa.me). */
const whatsAppText = async (page) => {
  const href = (await page.locator('a.whatsapp-fab').getAttribute('href')) ?? ''
  const url = new URL(href)
  expect(`${url.origin}${url.pathname}`).toBe('https://wa.me/351935745663')
  return url.searchParams.get('text')
}

test.describe('o canonical não leva a query (SEO-05)', () => {
  for (const [visited, expected] of [
    ['/categoria/almofada?utm_source=audit&cor=2', '/categoria/almofada'],
    ['/categoria/almofada/agate?utm_source=whatsapp', '/categoria/almofada/agate'],
    ['/sobre?x=1#topo', '/sobre'],
    ['/?utm_campaign=natal', '/'],
    ['/categoria/material-cozinha/avental-liso?tipo=avental', '/categoria/material-cozinha/avental-liso'],
  ]) {
    test(`${visited} → ${expected}`, async ({ page }) => {
      await page.goto(visited)
      await expect(page.locator('main').first()).toBeVisible()

      await expect(canonical(page)).toHaveAttribute('href', `${SITE}${expected}`)
      await expect(ogUrl(page)).toHaveAttribute('content', `${SITE}${expected}`)
    })
  }

  test('ao navegar dentro da loja com uma query, o canonical continua a ser o da página', async ({ page }) => {
    await page.goto('/categoria/almofada')
    await expect(page.getByRole('heading', { level: 1, name: 'Almofada' })).toBeVisible()
    await page.evaluate(() => window.history.pushState({}, '', '/categoria/almofada?cor=2&utm_source=x'))

    await expect(canonical(page)).toHaveAttribute('href', `${SITE}/categoria/almofada`)
    await page.goto('/pesquisa?q=azul')
    await expect(canonical(page)).toHaveAttribute('href', `${SITE}/pesquisa`)
  })
})

test.describe('o WhatsApp leva o modelo (RP-13)', () => {
  test('fora de um modelo o texto é o de sempre', async ({ page }) => {
    for (const path of ['/', '/categorias', '/categoria/almofada', '/contacto']) {
      await page.goto(path)
      await expect(page.locator('a.whatsapp-fab')).toBeVisible()
      expect(await whatsAppText(page), path).toBe(DEFAULT_TEXT)
    }
  })

  test('na página de um modelo leva o nome, a categoria, a cor, a medida, o EAN e o endereço, e acompanha a escolha', async ({
    page,
  }) => {
    await page.goto('/categoria/almofada/foglia?utm_source=email')
    await expect(page.getByRole('heading', { level: 1, name: 'Foglia' })).toBeVisible()

    // A primeira cor e a primeira medida, que são as que a página mostra de início. O endereço é o canónico, sem a query.
    expect(await whatsAppText(page)).toBe(
      `Olá! Gostaria de saber mais sobre o modelo Foglia (Almofada), cor Azul Ciano, medida 35x50 cm, EAN 5606044506574. ${SITE}/categoria/almofada/foglia`,
    )

    await page.getByRole('button', { name: '60x60 cm' }).click()
    await page.getByRole('button', { name: 'Bege', exact: true }).or(page.getByTitle('Bege')).first().click()
    expect(await whatsAppText(page)).toBe(
      `Olá! Gostaria de saber mais sobre o modelo Foglia (Almofada), cor Bege, medida 60x60 cm, EAN 5606044506734. ${SITE}/categoria/almofada/foglia`,
    )
  })

  test('um assento diz «altura», e um modelo com uma só cor não a menciona', async ({ page }) => {
    await page.goto('/categoria/assento/liso')
    await expect(page.getByRole('heading', { level: 1, name: 'Liso' })).toBeVisible()

    const text = await whatsAppText(page)
    expect(text).toMatch(/^Olá! Gostaria de saber mais sobre o modelo Liso \(Assento\), altura 32mm, EAN \d{13}\. /)
    expect(text).not.toMatch(/cor /)
  })

  test('um artigo único não tem medida', async ({ page }) => {
    await page.goto('/categoria/oculos/adulto')
    await expect(page.getByRole('heading', { level: 1, name: 'Adulto' })).toBeVisible()

    const text = await whatsAppText(page)
    expect(text).toMatch(/^Olá! Gostaria de saber mais sobre o modelo Adulto \(Óculos\), EAN \d{13}\. /)
    expect(text).not.toMatch(/medida|altura|cor /)
  })

  test('ao sair do modelo o botão volta ao texto de sempre', async ({ page }) => {
    await page.goto('/categoria/almofada/foglia')
    await expect(page.getByRole('heading', { level: 1, name: 'Foglia' })).toBeVisible()
    expect(await whatsAppText(page)).toContain('Foglia')

    await page.getByRole('link', { name: 'Almofada', exact: true }).first().click()
    await expect(page).toHaveURL(/\/categoria\/almofada$/)
    expect(await whatsAppText(page)).toBe(DEFAULT_TEXT)
  })
})
