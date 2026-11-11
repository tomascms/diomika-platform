// @ts-check
// Com o armazenamento do site bloqueado a loja abre e junta artigos (auditoria: FE-11).
//
// Emula o que o Chrome e o Firefox fazem quando o visitante bloqueia os dados do site: aceder a `localStorage` ou a
// `sessionStorage` lança SecurityError. Antes, o `sessionStorage` bloqueado deixava a página em branco (images.js
// acedia-lhe ao carregar) e o `localStorage` bloqueado fazia o botão «Adicionar ao pedido» não responder.
import { test, expect } from '@playwright/test'
import { mockApi } from './helpers.js'

const PEDIDO_ID = '3f2a9c1b-6d4e-4f10-9a77-0c5d2e8b1a34'

/**
 * @param {import('@playwright/test').Page} page
 * @param {{ local?: boolean, session?: boolean }} blocked
 * @returns {Promise<string[]>} os erros de JavaScript da página, ao vivo
 */
async function blockStorage(page, { local = false, session = false }) {
  await page.addInitScript(
    ({ local: blockLocal, session: blockSession }) => {
      const block = (name) =>
        Object.defineProperty(window, name, {
          configurable: true,
          get() {
            throw new DOMException('The operation is insecure.', 'SecurityError')
          },
        })
      if (blockLocal) block('localStorage')
      if (blockSession) block('sessionStorage')
    },
    { local, session },
  )
  /** @type {string[]} */
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  return errors
}

const turnstileOk = (page) =>
  page.route(
    (url) => url.hostname === 'challenges.cloudflare.com' && url.pathname === '/turnstile/v0/api.js',
    (route) =>
      route.fulfill({
        contentType: 'text/javascript',
        body: "window.turnstile = { render: (el, options) => { options.callback('token-e2e'); return 'e2e' }, reset() {}, remove() {} }",
      }),
  )

/** Sem armazenamento a escolha de cookies não se guarda: recusa-se no banner, que aparece sempre. */
async function dismissBanner(page) {
  const refuse = page.getByRole('region', { name: 'Consentimento de cookies' }).getByRole('button', { name: 'Recusar' })
  await refuse.click()
  await expect(refuse).toHaveCount(0)
}

const BLOCKED = [
  { name: 'sessionStorage bloqueado', blocked: { session: true } },
  { name: 'localStorage bloqueado', blocked: { local: true } },
  { name: 'os dois bloqueados', blocked: { local: true, session: true } },
]

for (const { name, blocked } of BLOCKED) {
  test.describe(name, () => {
    test('a loja abre: o início mostra as categorias e a página não rebenta', async ({ page }) => {
      await mockApi(page)
      const errors = await blockStorage(page, blocked)
      await page.goto('/')

      // Antes: `#app` sem filhos e um erro «Failed to read the 'sessionStorage' property…».
      await expect(page.locator('main .cat-grid').getByRole('link')).toHaveCount(6)
      expect(errors).toEqual([])
    })

    test('o produto junta-se ao pedido, que se vê no cabeçalho e na página do pedido', async ({ page }) => {
      await mockApi(page)
      const errors = await blockStorage(page, blocked)
      await page.goto('/categoria/almofada/agate')
      if (blocked.local) await dismissBanner(page)

      await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()
      await expect(page.getByRole('status').filter({ hasText: 'adicionadas ao pedido' })).toBeVisible()
      await expect(page.locator('.cart-badge')).toBeVisible()

      await page.getByRole('button', { name: 'Ver pedido' }).click()
      await expect(page).toHaveURL(/\/carrinho$/)
      await expect(page.locator('article.line')).toHaveCount(1)
      await expect(page.locator('article.line')).toContainText('Agate')
      expect(errors).toEqual([])
    })
  })
}

test.describe('localStorage bloqueado: o pedido fica em memória e o visitante é avisado', () => {
  test('avisa na página do produto e na do pedido, com saídas por WhatsApp e pelo formulário de contacto', async ({
    page,
  }) => {
    await mockApi(page)
    await blockStorage(page, { local: true })
    await page.goto('/categoria/almofada/agate')
    await dismissBanner(page)

    // Antes de tentar guardar não há nada a dizer.
    await expect(page.locator('.storage-notice')).toHaveCount(0)
    await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()

    const notice = page.locator('.storage-notice')
    await expect(notice).toContainText(
      'O seu navegador está a bloquear o armazenamento do site: o pedido só se mantém enquanto não fechar nem recarregar a página.',
    )
    await expect(notice.getByRole('link', { name: 'WhatsApp' })).toHaveAttribute('href', /^https:\/\/wa\.me\/351935745663/)
    await expect(notice.getByRole('link', { name: 'formulário de contacto' })).toHaveAttribute('href', '/contacto')

    await page.getByRole('button', { name: 'Ver pedido' }).click()
    await expect(page.locator('.storage-notice')).toBeVisible()
  })

  test('com o armazenamento a funcionar não há aviso nenhum', async ({ page }) => {
    await mockApi(page)
    await page.addInitScript(() => localStorage.setItem('diomika_cookie_consent', 'rejected'))
    await page.goto('/categoria/almofada/agate')
    await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()
    await expect(page.getByRole('status').filter({ hasText: 'adicionadas ao pedido' })).toBeVisible()

    await expect(page.locator('.storage-notice')).toHaveCount(0)
  })
})

test.describe('os formulários enviam-se com o armazenamento bloqueado', () => {
  test('pedido de orçamento: junta o artigo, envia e mostra a referência', async ({ page }) => {
    await mockApi(page)
    const errors = await blockStorage(page, { local: true, session: true })
    await turnstileOk(page)
    /** @type {any[]} */
    const sent = []
    await page.route(
      (url) => url.pathname === '/api/orcamentos',
      (route) => {
        sent.push({ body: route.request().postDataJSON(), key: route.request().headers()['idempotency-key'] })
        return route.fulfill({ json: { status: 'success', id: PEDIDO_ID } })
      },
    )
    await page.goto('/categoria/almofada/agate')
    await dismissBanner(page)
    await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()
    await page.getByRole('button', { name: 'Ver pedido' }).click()

    await page.getByLabel('Nome').fill('Ana Silva')
    await page.getByLabel('Email').fill('ana@empresa.pt')
    await page.getByRole('button', { name: 'Enviar pedido de orçamento' }).click()

    // Antes, a chave de idempotência (sessionStorage) lançava e o pedido nem saía.
    await expect(page.locator('.success-card')).toContainText('Pedido n.º 3f2a9c1b')
    expect(sent).toHaveLength(1)
    expect(sent[0].key).toMatch(/^[0-9a-f-]{36}$/)
    expect(errors).toEqual([])
  })

  test('contacto: envia-se com o sessionStorage bloqueado', async ({ page }) => {
    await mockApi(page)
    const errors = await blockStorage(page, { session: true })
    await page.addInitScript(() => localStorage.setItem('diomika_cookie_consent', 'rejected'))
    await turnstileOk(page)
    /** @type {any[]} */
    const sent = []
    await page.route(
      (url) => url.pathname === '/api/contacto',
      (route) => {
        sent.push(route.request().headers()['idempotency-key'])
        return route.fulfill({ json: { status: 'success' } })
      },
    )
    await page.goto('/contacto')
    await page.getByLabel('Nome').fill('Ana Silva')
    await page.getByLabel('Email').fill('ana@empresa.pt')
    await page.getByLabel('Mensagem').fill('Gostaria de saber mais sobre as almofadas.')
    await page.getByRole('button', { name: 'Enviar mensagem' }).click()

    await expect(page.getByText('Mensagem enviada.')).toBeVisible()
    expect(sent).toHaveLength(1)
    expect(errors).toEqual([])
  })
})
