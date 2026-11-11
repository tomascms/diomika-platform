// @ts-check
// Fabricante ou importador e avisos de segurança na ficha do modelo (auditoria LEGAL-12, Reg. UE 2023/988, art. 19.º).
//
// A API manda, por modelo, quatro campos opcionais (fabricante_nome, fabricante_morada, fabricante_email, avisos) e a
// ficha mostra os que o cliente preencheu. Sem nada preenchido, a ficha fica como estava.
import { test, expect } from '@playwright/test'
import { fixture, mockApi } from './helpers.js'

const FOGLIA = 'catalogo/almofada/modelo-detalhe/slug/almofada/foglia'

/**
 * A Foglia como a API a manda, com os campos que se passarem.
 * @param {import('@playwright/test').Page} page
 * @param {Record<string, unknown>} values
 */
async function serveFoglia(page, values) {
  const foglia = await fixture(FOGLIA)
  await page.route(
    (url) => url.pathname === `/api/${FOGLIA}`,
    (route) => route.fulfill({ json: { ...foglia, ...values } }),
  )
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
  await page.addInitScript(() => localStorage.setItem('diomika_cookie_consent', 'rejected'))
})

test('a ficha mostra o fabricante, a morada, o email (ligação) e os avisos, um por linha', async ({
  page,
}) => {
  await serveFoglia(page, {
    fabricante_nome: 'Têxteis do Ave, Lda.',
    fabricante_morada: 'Rua da Fábrica 1, 4800-000 Guimarães, Portugal',
    fabricante_email: 'geral@texteis-ave.example',
    avisos: 'Manter longe do fogo.\nNão deixar crianças sem vigilância.',
  })
  await page.goto('/categoria/almofada/foglia')

  const maker = page.locator('[data-spec="fabricante"]')
  await expect(maker.locator('dt')).toHaveText('Fabricante ou importador')
  await expect(maker).toContainText('Têxteis do Ave, Lda.')
  await expect(maker).toContainText('Rua da Fábrica 1, 4800-000 Guimarães, Portugal')
  await expect(maker.getByRole('link', { name: 'geral@texteis-ave.example' })).toHaveAttribute(
    'href',
    'mailto:geral@texteis-ave.example',
  )

  const warnings = page.locator('[data-spec="avisos"]')
  await expect(warnings.locator('dt')).toHaveText('Avisos de segurança')
  await expect(warnings.locator('dd')).toHaveText(
    'Manter longe do fogo.\nNão deixar crianças sem vigilância.',
  )
  await expect(warnings.locator('dd')).toHaveCSS('white-space', 'pre-line')
})

test('só o que está preenchido aparece: sem avisos, sem email', async ({ page }) => {
  await serveFoglia(page, {
    fabricante_nome: 'Importadora Norte, Lda.',
    fabricante_morada: '  ',
    fabricante_email: null,
    avisos: '',
  })
  await page.goto('/categoria/almofada/foglia')

  const maker = page.locator('[data-spec="fabricante"]')
  await expect(maker).toContainText('Importadora Norte, Lda.')
  await expect(maker.locator('a')).toHaveCount(0)
  await expect(page.locator('[data-spec="avisos"]')).toHaveCount(0)
})

test('sem nenhum dos campos (o modelo de hoje), a ficha não mostra o bloco', async ({ page }) => {
  await page.goto('/categoria/almofada/foglia')
  await expect(page.locator('.specs-panel')).toBeVisible()

  await expect(page.locator('[data-spec="fabricante"]')).toHaveCount(0)
  await expect(page.locator('[data-spec="avisos"]')).toHaveCount(0)
  await expect(page.getByText('Fabricante ou importador')).toHaveCount(0)
})

test('com tudo vazio, nem o painel de especificações mostra linhas do fabricante', async ({
  page,
}) => {
  await serveFoglia(page, {
    fabricante_nome: '',
    fabricante_morada: '',
    fabricante_email: '',
    avisos: '   ',
  })
  await page.goto('/categoria/almofada/foglia')

  await expect(page.locator('.specs-panel')).toBeVisible()
  await expect(page.locator('[data-spec]')).toHaveCount(0)
})
