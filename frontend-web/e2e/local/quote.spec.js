// @ts-check
// Pedido de orçamento com recibo (auditoria: BR-06, RP-05, FE-14, LEGAL-10).
//
// A API é simulada (mockApi) e o Turnstile dá sempre token; o teste vê o que a loja envia e o que mostra
// quando a resposta chega. O banner de cookies não aparece (escolha já feita), senão tapava o botão.
import { test, expect } from '@playwright/test'
import { mockApi } from './helpers.js'
import { CONSENT_VERSION } from '../../src/lib/consent.js'

const PEDIDO_ID = '3f2a9c1b-6d4e-4f10-9a77-0c5d2e8b1a34'
const NIF_ERROR = 'NIF inválido: o dígito de controlo não confere. Confira os 9 dígitos.'

const line = (n, quantidade = 12) => ({
  ean: `56060440000${String(n).padStart(2, '0')}`,
  numero_cor: 1,
  quantidade,
  modeloNome: `Modelo ${n}`,
  dimensoes: '45x45',
  corNome: 'Azul',
  carrinho_step: 6,
  carrinho_min: 6,
})

/**
 * Abre /carrinho com um pedido já feito, um Turnstile que dá token e uma API que aceita o pedido
 * (ou responde como `reply`). Devolve, ao vivo, os corpos dos POST a /api/orcamentos.
 * @param {import('@playwright/test').Page} page
 */
async function openQuote(
  page,
  { lines = [line(1)], reply = { json: { status: 'success', id: PEDIDO_ID } }, consent = 'rejected' } = {},
) {
  await mockApi(page)
  await page.addInitScript(
    ([cart, consent]) => {
      localStorage.setItem('diomika_cookie_consent', consent)
      localStorage.setItem('diomika_cart', JSON.stringify(cart))
    },
    [lines, consent],
  )
  await page.route(
    (url) => url.hostname === 'challenges.cloudflare.com' && url.pathname === '/turnstile/v0/api.js',
    (route) =>
      route.fulfill({
        contentType: 'text/javascript',
        body: "window.turnstile = { render: (el, options) => { options.callback('token-e2e'); return 'e2e' }, reset() {}, remove() {} }",
      }),
  )
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

async function fillBuyer(page) {
  await page.getByLabel('Nome').fill('Ana Silva')
  await page.getByLabel('Email').fill('ana@example.com')
}

const send = (page) => page.getByRole('button', { name: 'Enviar pedido de orçamento' }).click()

test.describe('o formulário', () => {
  test('pede empresa, NIF, localidade e tipo de cliente, tudo facultativo, e diz o que é obrigatório', async ({
    page,
  }) => {
    await openQuote(page)
    const form = page.locator('form.quote-form')

    await expect(page.locator('.form-section')).toContainText('Os campos com * são obrigatórios.')
    for (const name of ['Nome', 'Email']) {
      await expect(form.getByLabel(name)).toHaveAttribute('required', '')
    }
    for (const name of ['Telefone (opcional)', 'Empresa (opcional)', 'NIF (opcional)', 'Localidade (opcional)']) {
      await expect(form.getByLabel(name)).toBeVisible()
      await expect(form.getByLabel(name)).not.toHaveAttribute('required', /.*/)
    }
    await expect(form.getByLabel('Observações (opcional)')).toBeVisible()

    // «Compro como»: duas opções, nenhuma pré-seleccionada (quem não escolhe fica sem tipo, e na dúvida vale a parte para consumidores).
    const group = form.getByRole('group', { name: 'Compro como (opcional)' })
    await expect(group.getByRole('radio')).toHaveCount(2)
    await expect(group.getByRole('radio', { name: 'Empresa' })).not.toBeChecked()
    await expect(group.getByRole('radio', { name: 'Particular' })).not.toBeChecked()
  })

  test('o aviso de privacidade e de pedido não vinculativo está junto ao botão, com a ligação à política', async ({
    page,
  }) => {
    await openQuote(page)
    const form = page.locator('form.quote-form')
    const submit = form.getByRole('button', { name: 'Enviar pedido de orçamento' })
    // O parágrafo imediatamente antes do botão (a ligação às condições de venda fica logo depois dele).
    const notice = submit.locator('xpath=preceding-sibling::p[1]')

    await expect(notice).toHaveText(
      'O pedido não é vinculativo: a venda só se conclui quando aceitar a nossa proposta. Usamos estes dados para lhe responder. Política de Privacidade.',
    )
    const link = notice.getByRole('link', { name: 'Política de Privacidade' })
    await expect(link).toHaveAttribute('href', '/privacidade')
    // Noutro separador: no mesmo, o que já se escreveu no formulário perdia-se.
    await expect(link).toHaveAttribute('target', '_blank')
  })

  test('«Adicionar mais artigos» está no topo do pedido e leva ao catálogo', async ({ page }) => {
    await openQuote(page)
    const link = page.locator('.lines-head').getByRole('link', { name: 'Adicionar mais artigos' })

    await expect(link).toBeVisible()
    await link.click()
    await expect(page).toHaveURL(/\/categorias$/)
  })
})

test.describe('envio', () => {
  test('como empresa: leva todos os campos e o sucesso mostra a referência do pedido', async ({ page }) => {
    const sent = await openQuote(page)
    await fillBuyer(page)
    await page.getByLabel('Telefone (opcional)').fill(' 912 345 678 ')
    await page.getByRole('radio', { name: 'Empresa' }).check()
    await page.getByLabel('Empresa (opcional)').fill('Têxteis do Ave, Lda')
    await page.getByLabel('NIF (opcional)').fill('PT 508 651 557')
    await page.getByLabel('Localidade (opcional)').fill('Guimarães')
    await page.getByLabel('Observações (opcional)').fill('Entrega em maio')
    await send(page)

    const success = page.locator('.success-card')
    await expect(success.getByRole('heading', { name: 'Pedido enviado com sucesso.' })).toBeVisible()
    // Os 8 primeiros caracteres do id: os mesmos que o email para a equipa mostra.
    await expect(success).toContainText('Pedido n.º 3f2a9c1b')
    await expect(success).toContainText(
      'Guarde este número: indique-o se nos contactar por WhatsApp ou telefone.',
    )
    const whatsapp = success.getByRole('link', { name: 'Falar no WhatsApp' })
    const href = (await whatsapp.getAttribute('href')) ?? ''
    expect(decodeURIComponent(href.split('?text=')[1])).toBe(
      'Olá! Acabei de enviar o pedido de orçamento n.º 3f2a9c1b no site Diomika.',
    )

    expect(sent).toHaveLength(1)
    expect(sent[0]).toMatchObject({
      nome: 'Ana Silva',
      email: 'ana@example.com',
      contacto: '912 345 678',
      tipo_cliente: 'empresa',
      empresa: 'Têxteis do Ave, Lda',
      nif: 'PT 508 651 557', // a API guarda só os 9 dígitos
      localidade: 'Guimarães',
      observacoes: 'Entrega em maio',
    })
    expect(sent[0].linhas).toEqual([{ ean: '5606044000001', numero_cor: 1, quantidade: 12 }])
  })

  test('como particular, com NIF estrangeiro: aceite', async ({ page }) => {
    const sent = await openQuote(page)
    await fillBuyer(page)
    await page.getByRole('radio', { name: 'Particular' }).check()
    await page.getByLabel('NIF (opcional)').fill('ES B12345678')
    await send(page)

    await expect(page.locator('.success-card')).toContainText('Pedido n.º 3f2a9c1b')
    expect(sent[0]).toMatchObject({ tipo_cliente: 'particular', nif: 'ES B12345678' })
  })

  test('só com nome e email: os campos novos seguem a null (pedido como o de antes)', async ({ page }) => {
    const sent = await openQuote(page)
    await fillBuyer(page)
    await send(page)

    await expect(page.locator('.success-card')).toContainText('Pedido n.º 3f2a9c1b')
    expect(sent[0]).toMatchObject({
      contacto: null,
      tipo_cliente: null,
      empresa: null,
      nif: null,
      localidade: null,
      observacoes: null,
    })
  })

  test('carrinho com 20 linhas e quantidades no limite: o pedido envia-se', async ({ page }) => {
    const lines = Array.from({ length: 20 }, (_, n) => line(n + 1, 6000))
    const sent = await openQuote(page, { lines })
    await fillBuyer(page)
    await send(page)

    await expect(page.locator('.success-card')).toContainText('Pedido n.º 3f2a9c1b')
    expect(sent[0].linhas).toHaveLength(20)
    expect(sent[0].linhas.every((l) => l.quantidade === 6000)).toBe(true)
    await expect(page.locator('.submitted-summary p')).toHaveCount(20)
  })

  test('sem consentimento de analytics o pedido não leva origem', async ({ page }) => {
    const sent = await openQuote(page)
    await fillBuyer(page)
    await send(page)

    await expect(page.locator('.success-card')).toBeVisible()
    expect(sent[0].origem).toBeNull()
  })

  test('com consentimento o pedido leva a origem (página de entrada) e nada de pessoal', async ({ page }) => {
    const consent = JSON.stringify({ state: 'accepted', version: CONSENT_VERSION, date: new Date().toISOString() })
    const sent = await openQuote(page, { consent })
    await fillBuyer(page)
    await send(page)

    await expect(page.locator('.success-card')).toBeVisible()
    expect(sent[0].origem).toEqual({ entrada: '/carrinho' })
  })

  test('sem referência na resposta (API antiga): o sucesso não inventa um número', async ({ page }) => {
    await openQuote(page, { reply: { json: { status: 'success' } } })
    await fillBuyer(page)
    await send(page)

    await expect(page.locator('.success-card')).toContainText('Pedido enviado com sucesso.')
    await expect(page.locator('.success-card')).not.toContainText('Pedido n.º')
    const href = (await page.getByRole('link', { name: 'Falar no WhatsApp' }).getAttribute('href')) ?? ''
    expect(decodeURIComponent(href.split('?text=')[1])).toBe(
      'Olá! Acabei de enviar um pedido de orçamento no site Diomika.',
    )
  })
})

test.describe('erros junto ao campo', () => {
  test('NIF português com o dígito de controlo errado: mensagem em português, foco no campo e nada se envia', async ({
    page,
  }) => {
    const sent = await openQuote(page)
    await fillBuyer(page)
    await page.getByRole('radio', { name: 'Particular' }).check() // o tipo não livra de um NIF português errado
    const nif = page.getByLabel('NIF (opcional)')
    await nif.fill('508651558')
    await send(page)

    const error = page.locator('#nif-erro')
    await expect(error).toHaveText(NIF_ERROR)
    await expect(nif).toBeFocused()
    await expect(nif).toHaveAttribute('aria-invalid', 'true')
    await expect(nif).toHaveAttribute('aria-describedby', 'nif-erro')
    expect(sent).toHaveLength(0)

    // Corrigir o campo tira o erro logo; a seguir o pedido segue.
    await nif.fill('508651557')
    await expect(error).toHaveCount(0)
    await expect(nif).not.toHaveAttribute('aria-invalid', /.*/)
    await send(page)
    await expect(page.locator('.success-card')).toContainText('Pedido n.º 3f2a9c1b')
    expect(sent).toHaveLength(1)
  })

  test('nome e email em falta: um erro por campo, o primeiro com o foco, e nada se envia', async ({ page }) => {
    const sent = await openQuote(page)
    await send(page)

    await expect(page.locator('#nome-erro')).toHaveText('Preencha «Nome».')
    await expect(page.locator('#email-erro')).toHaveText('Preencha «Email».')
    await expect(page.getByLabel('Nome')).toBeFocused()
    for (const id of ['nome', 'email']) {
      await expect(page.locator(`#${id}`)).toHaveAttribute('aria-invalid', 'true')
      await expect(page.locator(`#${id}`)).toHaveAttribute('aria-describedby', `${id}-erro`)
    }
    expect(sent).toHaveLength(0)
  })

  test('email sem arroba: mensagem com um exemplo', async ({ page }) => {
    const sent = await openQuote(page)
    await page.getByLabel('Nome').fill('Ana Silva')
    await page.getByLabel('Email').fill('ana.example.com')
    await send(page)

    await expect(page.locator('#email-erro')).toHaveText(
      'Indique um email válido, por exemplo nome@empresa.pt.',
    )
    await expect(page.getByLabel('Email')).toBeFocused()
    expect(sent).toHaveLength(0)
  })
})
