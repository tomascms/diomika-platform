// @ts-check
// Erros claros e validação (auditoria: FE-09, A11Y-07).
//
// A API é simulada (mockApi). Para fazer falhar um pedido, o teste regista uma rota por cima; `route.fallback()`
// devolve o pedido à fixture, para a segunda tentativa («Tentar de novo») resultar.
import { test, expect } from '@playwright/test'
import { mockApi } from './helpers.js'

const PEDIDO_ID = '3f2a9c1b-6d4e-4f10-9a77-0c5d2e8b1a34'
const WHATSAPP = 'https://wa.me/351935745663'
const LINE = {
  ean: '5606044000012',
  numero_cor: 1,
  quantidade: 12,
  modeloNome: 'Agate',
  dimensoes: '45x45',
  corNome: 'Azul',
  carrinho_step: 12,
  carrinho_min: 12,
}

/** O banner de cookies (fixo, em baixo) taparia botões: entra-se com a escolha feita. */
const rejectCookies = (page) =>
  page.addInitScript(() => localStorage.setItem('diomika_cookie_consent', 'rejected'))

/** Um Turnstile que dá token logo (os formulários só enviam com token). */
const turnstileOk = (page) =>
  page.route(
    (url) => url.hostname === 'challenges.cloudflare.com' && url.pathname === '/turnstile/v0/api.js',
    (route) =>
      route.fulfill({
        contentType: 'text/javascript',
        body: "window.turnstile = { render: (el, options) => { options.callback('token-e2e'); return 'e2e' }, reset() {}, remove() {} }",
      }),
  )

/**
 * Pedidos que `match` apanha ficam em baixo (`respond`) até `fix()`: a seguir passam para a fixture. Estar em
 * baixo até ao fim da verificação (e não «falhar uma vez») evita que um segundo pedido da mesma página, feito
 * enquanto o primeiro falha, apanhe a fixture e esconda o erro.
 */
async function outage(page, match, respond) {
  let down = true
  await page.route(match, (route) => (down ? respond(route) : route.fallback()))
  return {
    fix: () => {
      down = false
    },
  }
}

const is = (fragment) => (url) => url.pathname.includes(fragment)

/** O estado de erro: o título, e as acções que o visitante tem. */
const errorState = (page) => page.locator('.error-state')

async function expectHelpAlternatives(scope) {
  await expect(scope.getByRole('link', { name: 'Falar no WhatsApp' })).toHaveAttribute(
    'href',
    new RegExp(`^${WHATSAPP}`),
  )
  const phone = scope.getByRole('link', { name: 'Ligar 935 745 663' })
  await expect(phone).toHaveAttribute('href', 'tel:+351935745663')
}

test.describe('página de produto', () => {
  test('produto que já não existe (404): diz-o, com saída para a categoria e sem «Tentar de novo»', async ({
    page,
  }) => {
    await mockApi(page)
    await rejectCookies(page)
    await page.goto('/categoria/almofada/nao-existe')

    const state = errorState(page)
    await expect(state.getByRole('heading', { name: 'Este produto já não está disponível' })).toBeVisible()
    await expect(state).toHaveAttribute('role', 'alert')
    await expect(state.getByRole('link', { name: 'Ver outros modelos' })).toHaveAttribute('href', '/categoria/almofada')
    // Tentar de novo não resolve um 404, e o servidor não está em baixo: nem botão nem contactos de emergência.
    await expect(state.getByRole('button', { name: 'Tentar de novo' })).toHaveCount(0)
    await expect(state.getByRole('link', { name: 'Falar no WhatsApp' })).toHaveCount(0)
  })

  test('servidor com erro (500): «O nosso servidor não respondeu», WhatsApp, telefone e «Tentar de novo» que resulta', async ({
    page,
  }) => {
    await mockApi(page)
    await rejectCookies(page)
    const server = await outage(page, is('/modelo-detalhe/'), (route) =>
      route.fulfill({ status: 500, json: { detail: 'Erro interno' } }),
    )
    await page.goto('/categoria/almofada/agate')

    const state = errorState(page)
    await expect(state.getByRole('heading', { name: 'O nosso servidor não respondeu' })).toBeVisible()
    // Nada de instruções técnicas nem de «Verifique a internet»: a culpa não é de quem visita.
    await expect(state).not.toContainText(/verifique|internet|Erro HTTP|hostname|Cloudflare/i)
    await expectHelpAlternatives(state)

    server.fix()
    await state.getByRole('button', { name: 'Tentar de novo' }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Agate' })).toBeVisible()
    await expect(errorState(page)).toHaveCount(0)
  })

  test('sem rede: o mesmo estado, e a segunda tentativa resulta', async ({ page }) => {
    await mockApi(page)
    await rejectCookies(page)
    const network = await outage(page, is('/modelo-detalhe/'), (route) => route.abort('internetdisconnected'))
    await page.goto('/categoria/almofada/agate')

    // Três tentativas (a primeira e as duas repetições automáticas do apiGet) antes de o estado aparecer.
    const state = errorState(page)
    await expect(state.getByRole('heading', { name: 'O nosso servidor não respondeu' })).toBeVisible()
    network.fix()
    await state.getByRole('button', { name: 'Tentar de novo' }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Agate' })).toBeVisible()
  })
})

test.describe('página de categoria', () => {
  test('categoria que não existe (404): diz-o, com saída para o catálogo e sem «Tentar de novo»', async ({
    page,
  }) => {
    await mockApi(page)
    await rejectCookies(page)
    await page.goto('/categoria/nao-existe')

    const state = errorState(page)
    await expect(state.getByRole('heading', { name: 'Esta categoria já não está disponível' })).toBeVisible()
    await expect(state.getByRole('link', { name: 'Ver o catálogo' })).toHaveAttribute('href', '/categorias')
    await expect(state.getByRole('button', { name: 'Tentar de novo' })).toHaveCount(0)
  })

  test('servidor em baixo (503): «Tentar de novo» e contactos; a segunda tentativa mostra os modelos', async ({
    page,
  }) => {
    await mockApi(page)
    await rejectCookies(page)
    // O 503 repete-se duas vezes sozinho (apiGet) antes de o estado aparecer.
    const server = await outage(page, is('/modelos-catalogo/'), (route) =>
      route.fulfill({ status: 503, json: { detail: 'Serviço indisponível' } }),
    )
    await page.goto('/categoria/almofada')

    const state = errorState(page)
    await expect(state.getByRole('heading', { name: 'O nosso servidor não respondeu' })).toBeVisible()
    await expectHelpAlternatives(state)
    server.fix()
    await state.getByRole('button', { name: 'Tentar de novo' }).click()
    await expect(page.locator('ul.grid').getByRole('link').first()).toBeVisible()
  })
})

test.describe('início, catálogo e pesquisa', () => {
  test('catálogo sem a lista de categorias: o mesmo estado, e voltar a tentar mostra as categorias', async ({
    page,
  }) => {
    await mockApi(page)
    await rejectCookies(page)
    const server = await outage(page, (url) => url.pathname === '/api/categorias', (route) =>
      route.fulfill({ status: 500, json: { detail: 'Erro interno' } }),
    )
    await page.goto('/categorias')

    const state = errorState(page)
    await expect(state.getByRole('heading', { name: 'O nosso servidor não respondeu' })).toBeVisible()
    await expect(page.getByRole('main')).not.toContainText(/Verifique a liga/i)
    server.fix()
    await state.getByRole('button', { name: 'Tentar de novo' }).click()
    await expect(page.locator('ul.grid').getByRole('link').first()).toBeVisible()
  })

  test('pesquisa com o servidor em baixo: o mesmo estado, sem «Verifique a internet»', async ({ page }) => {
    await mockApi(page)
    await rejectCookies(page)
    await page.route(is('/catalogo/search'), (route) =>
      route.fulfill({ status: 500, json: { detail: 'Erro interno' } }),
    )
    await page.goto('/pesquisa?q=almofada')

    const state = errorState(page)
    await expect(state.getByRole('heading', { name: 'O nosso servidor não respondeu' })).toBeVisible()
    await expect(page.getByRole('main')).not.toContainText(/Verifique a internet/i)
    await expectHelpAlternatives(state)
  })
})

test.describe('verificação anti-spam', () => {
  test('uma falha do Turnstile diz o que fazer, sem instruções de administrador, e oferece WhatsApp e telefone', async ({
    page,
  }) => {
    await mockApi(page)
    await rejectCookies(page)
    await page.route(
      (url) => url.hostname === 'challenges.cloudflare.com' && url.pathname === '/turnstile/v0/api.js',
      (route) =>
        route.fulfill({
          contentType: 'text/javascript',
          body: "window.turnstile = { render: (el, options) => { setTimeout(() => options['error-callback'](), 0); return 'e2e' }, reset() {}, remove() {} }",
        }),
    )
    await page.goto('/contacto')
    // O Turnstile só carrega quando se toca no formulário (PERF-05).
    await page.getByLabel('Nome').focus()

    const alert = page.getByRole('alert').filter({ hasText: 'verificação anti-spam' })
    await expect(alert).toContainText(
      'Não foi possível concluir a verificação anti-spam. Recarregue a página e tente de novo; se continuar, fale connosco por WhatsApp ou telefone.',
    )
    await expect(page.getByRole('main')).not.toContainText(/hostname|Cloudflare|autorize/i)
    await expectHelpAlternatives(page.locator('form.contact-form'))
  })
})

test.describe('formulário de contacto: erros junto ao campo (A11Y-07)', () => {
  /** @param {import('@playwright/test').Page} page */
  async function openContact(page, reply = { json: { status: 'success' } }) {
    await mockApi(page)
    await rejectCookies(page)
    await turnstileOk(page)
    /** @type {any[]} */
    const sent = []
    await page.route(
      (url) => url.pathname === '/api/contacto',
      (route) => {
        sent.push(route.request().postDataJSON())
        return route.fulfill(reply)
      },
    )
    await page.goto('/contacto')
    return sent
  }
  const send = (page) => page.getByRole('button', { name: 'Enviar mensagem' }).click()

  test('enviar vazio: um erro por campo obrigatório, ligado ao campo, e o foco no primeiro', async ({ page }) => {
    const sent = await openContact(page)
    await send(page)

    await expect(page.locator('#nome-erro')).toHaveText('Preencha «Nome».')
    await expect(page.locator('#email-erro')).toHaveText('Preencha «Email».')
    await expect(page.locator('#mensagem-erro')).toHaveText('Preencha «Mensagem».')
    for (const id of ['nome', 'email', 'mensagem']) {
      await expect(page.locator(`#${id}`)).toHaveAttribute('aria-invalid', 'true')
      await expect(page.locator(`#${id}`)).toHaveAttribute('aria-describedby', `${id}-erro`)
    }
    // O telefone e o assunto são facultativos: nada a dizer.
    for (const id of ['contacto', 'assunto']) {
      await expect(page.locator(`#${id}-erro`)).toHaveCount(0)
      await expect(page.locator(`#${id}`)).not.toHaveAttribute('aria-invalid', /.*/)
    }
    await expect(page.locator('#nome')).toBeFocused()
    expect(sent).toHaveLength(0)
  })

  test('corrigir um campo tira-lhe o erro; nome com um só carácter, email sem domínio e mensagem curta são recusados', async ({
    page,
  }) => {
    const sent = await openContact(page)
    await page.getByLabel('Nome').fill('A')
    await page.getByLabel('Email').fill('ana@empresa')
    await page.getByLabel('Mensagem').fill('curta')
    await send(page)

    await expect(page.locator('#nome-erro')).toHaveText('O nome: mínimo de 2 caracteres.')
    await expect(page.locator('#email-erro')).toHaveText('Indique um email válido, por exemplo nome@empresa.pt.')
    await expect(page.locator('#mensagem-erro')).toHaveText('A mensagem: mínimo de 10 caracteres.')

    await page.getByLabel('Nome').fill('Ana Silva')
    await expect(page.locator('#nome-erro')).toHaveCount(0)
    await expect(page.locator('#email-erro')).toBeVisible() // os outros ficam até se corrigirem

    await page.getByLabel('Email').fill('ana@empresa.pt')
    await page.getByLabel('Mensagem').fill('Gostaria de saber mais sobre as almofadas.')
    await send(page)
    await expect(page.getByText('Mensagem enviada.')).toBeVisible()
    expect(sent).toHaveLength(1)
  })

  test('nome só com espaços não passa', async ({ page }) => {
    const sent = await openContact(page)
    await page.getByLabel('Nome').fill('     ')
    await page.getByLabel('Email').fill('ana@empresa.pt')
    await page.getByLabel('Mensagem').fill('Gostaria de saber mais sobre as almofadas.')
    await send(page)

    await expect(page.locator('#nome-erro')).toHaveText('O nome: mínimo de 2 caracteres.')
    expect(sent).toHaveLength(0)
  })

  test('a API recusa um campo (422): a mensagem em português fica junto do campo', async ({ page }) => {
    await openContact(page, {
      status: 422,
      json: {
        detail: [
          { type: 'string_too_short', loc: ['body', 'mensagem'], msg: 'A mensagem: mínimo de 10 caracteres.' },
        ],
      },
    })
    await page.getByLabel('Nome').fill('Ana Silva')
    await page.getByLabel('Email').fill('ana@empresa.pt')
    await page.getByLabel('Mensagem').fill('Gostaria de saber mais sobre as almofadas.')
    await send(page)

    await expect(page.locator('#mensagem-erro')).toHaveText('A mensagem: mínimo de 10 caracteres.')
    await expect(page.locator('#mensagem')).toHaveAttribute('aria-invalid', 'true')
    await expect(page.locator('#mensagem')).toBeFocused()
    await expect(page.getByRole('alert').filter({ hasText: 'Corrija os campos assinalados' })).toBeVisible()
  })

  test('o servidor com erro (500): o aviso e os contactos; nada de mensagem técnica', async ({ page }) => {
    await openContact(page, { status: 500, json: { detail: 'Nao foi possivel enviar.' } })
    await page.getByLabel('Nome').fill('Ana Silva')
    await page.getByLabel('Email').fill('ana@empresa.pt')
    await page.getByLabel('Mensagem').fill('Gostaria de saber mais sobre as almofadas.')
    await send(page)

    await expect(page.getByRole('alert').filter({ hasText: 'Nao foi possivel enviar.' })).toBeVisible()
    await expectHelpAlternatives(page.locator('form.contact-form'))
  })
})

test.describe('pedido de orçamento: limites e erros da API (FE-09)', () => {
  /** @param {import('@playwright/test').Page} page */
  async function openQuote(page, reply = { json: { status: 'success', id: PEDIDO_ID } }) {
    await mockApi(page)
    await page.addInitScript(
      ([cart]) => {
        localStorage.setItem('diomika_cookie_consent', 'rejected')
        localStorage.setItem('diomika_cart', JSON.stringify(cart))
      },
      [[LINE]],
    )
    await turnstileOk(page)
    /** @type {any[]} */
    const sent = []
    await page.route(
      (url) => url.pathname === '/api/orcamentos',
      (route) => {
        sent.push(route.request().postDataJSON())
        return route.fulfill(reply)
      },
    )
    await page.goto('/carrinho')
    return sent
  }
  const send = (page) => page.getByRole('button', { name: 'Enviar pedido de orçamento' }).click()

  test('os campos levam os limites da API: nome 120, telefone 30, observações 5 000, nome com 2 e email com ponto no domínio', async ({
    page,
  }) => {
    await openQuote(page)

    await expect(page.locator('#nome')).toHaveAttribute('minlength', '2')
    await expect(page.locator('#nome')).toHaveAttribute('maxlength', '120')
    await expect(page.locator('#contacto')).toHaveAttribute('maxlength', '30')
    await expect(page.locator('#observacoes')).toHaveAttribute('maxlength', '5000')
    await expect(page.locator('#email')).toHaveAttribute('pattern', /\\\./)
  })

  test('nome só com espaços e email «a@b» (que o navegador aceitava) são recusados antes de enviar', async ({
    page,
  }) => {
    const sent = await openQuote(page)
    await page.getByLabel('Nome').fill('   ')
    await page.getByLabel('Email').fill('a@b')
    await send(page)

    await expect(page.locator('#nome-erro')).toHaveText('O nome: mínimo de 2 caracteres.')
    await expect(page.locator('#email-erro')).toHaveText('Indique um email válido, por exemplo nome@empresa.pt.')
    expect(sent).toHaveLength(0)
  })

  test('a API recusa campos (422): cada mensagem fica junto do seu campo e o resto vai para o aviso', async ({
    page,
  }) => {
    await openQuote(page, {
      status: 422,
      json: {
        detail: [
          { type: 'string_too_long', loc: ['body', 'observacoes'], msg: 'As observações: máximo de 5000 caracteres.' },
          { type: 'too_short', loc: ['body', 'linhas'], msg: 'As linhas do pedido: indique pelo menos 1.' },
        ],
      },
    })
    await page.getByLabel('Nome').fill('Ana Silva')
    await page.getByLabel('Email').fill('ana@empresa.pt')
    await send(page)

    await expect(page.locator('#observacoes-erro')).toHaveText('As observações: máximo de 5000 caracteres.')
    await expect(page.locator('#observacoes')).toBeFocused()
    // O que não é de nenhum campo vai para o aviso, em português e sem o «(ref: …)» a atrapalhar a leitura.
    await expect(page.getByRole('alert').filter({ hasText: 'As linhas do pedido: indique pelo menos 1.' })).toBeVisible()
    await expect(page.getByRole('main')).not.toContainText(/String should|Field required|valid email/i)
  })

  test('o servidor não responde: o aviso diz-o e oferece WhatsApp e telefone', async ({ page }) => {
    await openQuote(page, { status: 503, json: { detail: 'Serviço temporariamente indisponível.' } })
    await page.getByLabel('Nome').fill('Ana Silva')
    await page.getByLabel('Email').fill('ana@empresa.pt')
    await send(page)

    await expect(page.getByRole('alert').filter({ hasText: 'Serviço temporariamente indisponível.' })).toBeVisible()
    await expectHelpAlternatives(page.locator('form.quote-form'))
  })
})
