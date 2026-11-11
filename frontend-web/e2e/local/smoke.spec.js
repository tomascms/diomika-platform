// @ts-check
import { test, expect } from '@playwright/test'
import { fixture, mockApi } from './helpers.js'

test('início mostra as categorias da fixture', async ({ page }) => {
  await mockApi(page)
  await page.goto('/')

  const nomes = (await fixture('categorias')).map((categoria) => categoria.nome)
  const cartoes = page.locator('main .cat-grid').getByRole('link')
  // A página destaca seis categorias e todas vêm da fixture (nada vem da rede).
  await expect(cartoes).toHaveCount(6)
  for (const nome of await cartoes.allInnerTexts()) expect(nomes).toContain(nome.trim())
})

test('o Turnstile é simulado: /contacto abre sem pedidos para fora de localhost', async ({
  page,
}) => {
  await mockApi(page)
  await page.goto('/contacto')
  // O Turnstile só carrega quando se toca no formulário (PERF-05).
  await page.getByLabel('Nome').focus()

  // `window.turnstile` só existe se o script simulado foi servido e executado.
  await expect.poll(() => page.evaluate(() => typeof window.turnstile?.render)).toBe('function')
  await expect(page.getByText('Não foi possível carregar a verificação anti-spam')).toHaveCount(0)
})

test('um pedido para fora de localhost é abortado e reprova o teste', async ({ page }) => {
  // Falha esperada: se este teste passar, mockApi deixou de reprovar pedidos para fora de localhost.
  test.fail()
  await mockApi(page)
  await page.goto('/')

  await page.evaluate(() => fetch('https://example.com/').catch(() => {}))
})
