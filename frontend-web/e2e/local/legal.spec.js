// @ts-check
// Identificação do prestador, Livro de Reclamações, RAL, datas fixas e JSON-LD estático
// (auditoria: LEGAL-02, LEGAL-03, LEGAL-04, LEGAL-14, LEGAL-15, SEO-09).
//
// Os valores legais estão escritos à letra de propósito: se COMPANY mudar por engano, o teste
// reprova. O banner de cookies aparece (a chave do PostHog do harness é falsa): as leituras do
// DOM não dependem dele; o único clique (no rodapé) entra com a escolha de cookies já feita.
import { test, expect } from '@playwright/test'
import { mockApi } from './helpers.js'

const LEGAL_NAME = 'DIOMIKA INTERNACIONAL, UNIPESSOAL, LDA'
const COMPLAINTS_BOOK_URL = 'https://www.livroreclamacoes.pt'

// Um exemplo de cada tipo de página: início, catálogo, categoria, produto, pesquisa, pedido,
// contacto, institucionais e a página 404.
const PAGES = [
  '/',
  '/categorias',
  '/categoria/almofada',
  '/categoria/almofada/agate',
  '/pesquisa',
  '/carrinho',
  '/contacto',
  '/sobre',
  '/privacidade',
  '/termos',
  '/condicoes-de-venda',
  '/perguntas-frequentes',
  '/cookies',
  '/rota-que-nao-existe',
]

test.describe('rodapé de todas as páginas', () => {
  for (const url of PAGES) {
    test(url, async ({ page }) => {
      await mockApi(page)
      await page.goto(url)

      const footer = page.getByRole('contentinfo')
      // Identificação mínima do prestador (DL 7/2004, art. 10.º): o registo e a RAL ficam em «Informação legal».
      await expect(footer).toContainText(`${LEGAL_NAME} · NIPC 508 651 557`)
      await expect(footer).toContainText('Rua da Quintã, n.º 89, 4805-116 Caldas das Taipas')
      await expect(footer).not.toContainText('Matrícula')
      await expect(footer).not.toContainText('TRIAVE')
      await expect(footer.getByRole('link', { name: '935 745 663' })).toHaveAttribute('href', 'tel:+351935745663')
      await expect(footer.getByRole('link', { name: 'Contacto' })).toHaveAttribute('href', '/contacto')
      for (const [name, href] of [
        ['Condições de venda', '/condicoes-de-venda'],
        ['Perguntas frequentes', '/perguntas-frequentes'],
        ['Privacidade', '/privacidade'],
        ['Cookies', '/cookies'],
        ['Informação legal', '/termos'],
      ]) {
        await expect(footer.getByRole('link', { name, exact: true })).toHaveAttribute('href', href)
      }
      await expect(footer).toContainText(new RegExp(`© \\d{4} ${LEGAL_NAME}`))
      // Livro de Reclamações Eletrónico (DL 156/2005, art. 5.º-B): visível, não só presente no HTML.
      const book = footer.getByRole('link', { name: /Livro de Reclamações/ })
      await expect(book).toHaveAttribute('href', COMPLAINTS_BOOK_URL)
      await expect(book).toBeVisible()
      // Decisão do dono (ficha do cliente, Parte D, item 2): sem email público até o cliente o dar;
      // o contacto electrónico é o formulário. Nunca a caixa pessoal do prestador.
      await expect(page.locator('a[href^="mailto:"]')).toHaveCount(0)
      expect(await page.locator('body').innerText()).not.toMatch(/@(diomika|gmail)\./i)
    })
  }
})

test.describe('datas de actualização fixas', () => {
  for (const url of [
    '/termos',
    '/privacidade',
    '/cookies',
    '/condicoes-de-venda',
    '/perguntas-frequentes',
  ]) {
    test(url, async ({ page }) => {
      // Com o relógio noutro ano, uma data calculada em runtime mostraria esse ano.
      await page.clock.setFixedTime(new Date('2031-03-15T10:00:00Z'))
      await mockApi(page)
      await page.goto(url)

      const updated = page.getByText(/^Última actualização:/)
      await expect(updated).toHaveText(/^Última actualização: \d{1,2} de \p{L}+ de \d{4}$/u)
      await expect(updated).not.toContainText('2031')
    })
  }
})

test('Informação legal: identificação completa, Livro de Reclamações e RAL com o texto completo', async ({
  page,
}) => {
  await mockApi(page)
  await page.goto('/termos')

  // O mesmo nome na página, no título do separador e no rodapé (antes: «Aviso Legal» / «Termos e condições»).
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Informação legal')
  await expect(page).toHaveTitle('Informação legal | Diomika')

  const main = page.getByRole('main')
  await expect(main).toContainText(LEGAL_NAME)
  await expect(main).toContainText(
    'Matrícula na Conservatória do Registo Comercial e NIPC 508 651 557',
  )
  await expect(main.getByRole('link', { name: /formulário de contacto/i })).toHaveAttribute(
    'href',
    '/contacto',
  )
  await expect(main.getByRole('link', { name: /Livro de Reclamações Eletrónico/ })).toHaveAttribute(
    'href',
    COMPLAINTS_BOOK_URL,
  )
  await expect(main).not.toContainText('Foro competente: Portugal')

  const ral = main.locator('#resolucao-de-litigios')
  await expect(ral).toContainText(
    'TRIAVE – Centro de Arbitragem de Conflitos de Consumo do Ave, Tâmega e Sousa',
  )
  await expect(ral).toContainText('Rua Capitão Alfredo Guimarães, 1, 4800-019 Guimarães')
  await expect(ral).toContainText('253 422 410')
  await expect(ral).toContainText('Nos litígios de valor até 5 000 €')
  await expect(ral).toContainText('Lei n.º 24/96, art. 14.º, n.º 2')
  await expect(ral.getByRole('link', { name: 'www.triave.pt' })).toHaveAttribute(
    'href',
    'https://www.triave.pt',
  )
  await expect(ral.getByRole('link', { name: 'www.consumidor.gov.pt' })).toHaveAttribute(
    'href',
    'https://www.consumidor.gov.pt',
  )
  // A plataforma europeia de RLL fechou em 20-7-2025 (Reg. 2024/3228): não se liga a ela.
  await expect(page.locator('a[href*="ec.europa.eu/consumers/odr"]')).toHaveCount(0)
})

test('Informação legal: actividade, objecto do site, destinatários e responsabilidade dizem o mesmo que as condições de venda', async ({
  page,
}) => {
  await mockApi(page)
  // O banner de cookies (fixo, em baixo) taparia a ligação: entra-se com a escolha feita.
  await page.addInitScript(() => localStorage.setItem('diomika_cookie_consent', 'rejected'))
  await page.goto('/termos')
  const main = page.getByRole('main')
  const section = (name) =>
    main.locator('section', { has: page.getByRole('heading', { name, exact: true }) })

  // Actividade: a descrição do próprio site, sem código CAE (ficha do cliente, Parte D, item 1).
  await expect(section('Identificação')).toContainText(
    'Actividade: comércio por grosso de têxteis para o lar',
  )
  await expect(main).not.toContainText('CAE')

  // Objecto: catálogo e pedidos de orçamento; o pedido é um convite a contratar e não vincula (DL 7/2004, art. 32.º).
  await expect(section('Objecto do site')).toContainText(
    'O site destina-se à apresentação do catálogo e à recepção de pedidos de orçamento. ' +
      'O pedido de orçamento é um convite a contratar e não vincula o cliente nem a Diomika ' +
      '(Decreto-Lei n.º 7/2004, art. 32.º).',
  )

  // Destinatários: empresas e particulares; estes têm os direitos de consumidor das condições de venda.
  const destinatarios = section('Destinatários')
  await expect(destinatarios).toContainText(
    'O site destina-se a empresas e profissionais e também a particulares. ' +
      'Os particulares têm os direitos de consumidor descritos nas Condições gerais de venda.',
  )
  await expect(main).not.toContainText('catálogo B2B')

  // Responsabilidade: a ressalva da auditoria, à letra.
  await expect(section('Responsabilidade')).toContainText(
    'sem prejuízo dos direitos legais dos consumidores e da responsabilidade por dolo ou culpa grave',
  )

  // A ligação leva aos direitos de consumidor, na parte para consumidores das condições.
  await destinatarios.getByRole('link', { name: 'Condições gerais de venda' }).click()
  await expect(page).toHaveURL(/\/condicoes-de-venda#parte-consumidores$/)
  await expect(
    page.getByRole('heading', { name: 'Parte para consumidores: vendas a consumidores' }),
  ).toBeInViewport()
})

test('o endereço /termos#resolucao-de-litigios abre já na secção', async ({ page }) => {
  await mockApi(page)
  await page.goto('/termos#resolucao-de-litigios')

  await expect(page.getByRole('heading', { name: 'Resolução de litígios' })).toBeInViewport()
})

test.describe('JSON-LD estático', () => {
  test('o HTML servido, sem JavaScript, traz Organization com denominação legal e WebSite', async ({
    request,
  }) => {
    const html = await (await request.get('/')).text()
    const blocks = [
      ...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g),
    ].map((m) => JSON.parse(m[1]))

    expect(blocks.find((b) => b['@type'] === 'Organization')).toMatchObject({
      '@context': 'https://schema.org',
      name: 'Diomika',
      legalName: LEGAL_NAME,
      url: 'https://www.diomika.com/',
      logo: 'https://www.diomika.com/icon-512.png',
      vatID: 'PT508651557',
      telephone: '+351935745663',
      address: {
        '@type': 'PostalAddress',
        streetAddress: 'Rua da Quintã, n.º 89',
        postalCode: '4805-116',
        addressLocality: 'Caldas das Taipas',
        addressCountry: 'PT',
      },
    })
    expect(blocks.find((b) => b['@type'] === 'WebSite')).toMatchObject({
      '@context': 'https://schema.org',
      name: 'Diomika',
      url: 'https://www.diomika.com/',
    })
    // SearchAction (descontinuado pelo Google em 2024) e FAQPage (rich result restrito): fora.
    expect(JSON.stringify(blocks)).not.toMatch(/SearchAction|FAQPage/)
  })

  test('o Organization já não é injectado por JavaScript: no DOM há um só de cada', async ({
    page,
  }) => {
    await mockApi(page)
    await page.goto('/')

    const types = await page.evaluate(() =>
      [...document.querySelectorAll('script[type="application/ld+json"]')].map(
        (s) => JSON.parse(s.textContent || '{}')['@type'],
      ),
    )
    expect(types).toEqual(['Organization', 'WebSite'])
  })
})
