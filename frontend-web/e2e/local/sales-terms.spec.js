// @ts-check
// Condições gerais de venda, perguntas frequentes e os textos que as acompanham
// (auditoria: LEGAL-01 parte 1, LEGAL-11, RP-15).
//
// Os valores legais estão escritos à letra de propósito: se as constantes ou o texto mudarem por
// engano, o teste reprova. O pré-render e o sitemap não passam aqui (o servidor deste projecto não
// corre `prerender-seo.mjs`, que pede o catálogo à API): estão em scripts/static-pages.test.mjs.
import { test, expect } from '@playwright/test'
import { mockApi } from './helpers.js'

const MIN_ORDER = '500 € + IVA (615 € com IVA a 23 %)'
const PRICE_NOTE =
  'A oferta em linha dirige-se sobretudo a revendedores; a particulares, a proposta indica sempre o preço total com IVA e portes.'
const SELLS_TO = `Vendemos a lojas, hotelaria e particulares — pedido mínimo ${MIN_ORDER}.`
const CALL_NOTE = 'Chamada para a rede móvel nacional'
const LEGAL_NAME = 'DIOMIKA INTERNACIONAL, UNIPESSOAL, LDA'
const TRIAVE = 'TRIAVE – Centro de Arbitragem de Conflitos de Consumo do Ave, Tâmega e Sousa'

const CGV = '/condicoes-de-venda'
const FAQ = '/perguntas-frequentes'
const PAGES = [
  { url: CGV, h1: 'Condições Gerais de Venda', title: 'Condições gerais de venda | Diomika' },
  { url: FAQ, h1: 'Perguntas frequentes', title: 'Perguntas frequentes | Diomika' },
]

// Um pedido com uma linha: o formulário (e a ligação junto ao botão) só aparece com artigos.
const CART = [
  {
    ean: '5606044000012',
    numero_cor: 1,
    quantidade: 12,
    modeloNome: 'Agate',
    dimensoes: '45x45',
    corNome: 'Azul',
    carrinho_step: 12,
    carrinho_min: 12,
  },
]

/** O banner de cookies (fixo, em baixo) taparia as ligações do rodapé: entra-se com a escolha feita. */
const rejectCookies = (page) =>
  page.addInitScript(() => localStorage.setItem('diomika_cookie_consent', 'rejected'))
const seedCart = (page) =>
  page.addInitScript((items) => localStorage.setItem('diomika_cart', JSON.stringify(items)), CART)

test.describe('abrem por endereço directo', () => {
  for (const { url, h1, title } of PAGES) {
    test(url, async ({ page }) => {
      await mockApi(page)
      await page.goto(url)

      await expect(page.getByRole('heading', { level: 1 })).toHaveText(h1)
      await expect(page).toHaveTitle(title)
      await expect(page.getByRole('heading', { name: 'Página não encontrada' })).toHaveCount(0)
    })
  }
})

test('abrem pela navegação: ligações do rodapé, a partir do início e de uma página à outra', async ({
  page,
}) => {
  await mockApi(page)
  await rejectCookies(page)
  await page.goto('/')

  const footer = page.getByRole('contentinfo')
  await footer.getByRole('link', { name: 'Condições de venda' }).click()
  await expect(page).toHaveURL(new RegExp(`${CGV}$`))
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Condições Gerais de Venda')

  await footer.getByRole('link', { name: 'Perguntas frequentes' }).click()
  await expect(page).toHaveURL(new RegExp(`${FAQ}$`))
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Perguntas frequentes')
})

test('pedido de orçamento: ligação às condições logo a seguir ao botão de enviar, num novo separador', async ({
  page,
}) => {
  await mockApi(page)
  await seedCart(page)
  await page.goto('/carrinho')

  const form = page.locator('form.quote-form')
  const submit = form.getByRole('button', { name: 'Enviar pedido de orçamento' })
  const link = form.getByRole('link', { name: 'Condições gerais de venda' })
  await expect(submit).toBeVisible()
  await expect(link).toBeVisible()
  await expect(link).toHaveAttribute('href', CGV)
  await expect(link).toHaveAttribute('target', '_blank')
  // A linha é o irmão seguinte do botão. Abre noutro separador: no mesmo, o que já se escreveu no
  // formulário (nome, email, telefone) perdia-se.
  expect(
    await link.evaluate((a) =>
      a.parentElement?.previousElementSibling?.matches('button[type=submit]'),
    ),
  ).toBe(true)

  const [popup] = await Promise.all([page.context().waitForEvent('page'), link.click()])
  await expect(popup.getByRole('heading', { level: 1 })).toHaveText('Condições Gerais de Venda')
  await expect(page).toHaveURL(/\/carrinho$/)
})

test.describe('condições gerais de venda', () => {
  test('três partes (comum, empresas, consumidores) e as cláusulas de cada uma', async ({ page }) => {
    await mockApi(page)
    await page.goto(CGV)
    const main = page.getByRole('main')

    await expect(main.getByRole('heading', { level: 2 })).toHaveText([
      'Parte comum: todas as vendas',
      'Parte para empresas: vendas a empresas e profissionais',
      'Parte para consumidores: vendas a consumidores',
    ])
    await expect(main.getByText(/^Última actualização: \d{1,2} de \p{L}+ de \d{4}$/u)).toBeVisible()

    const [comum, empresas, consumidores] = await main.locator('section').all()
    await expect(comum.getByRole('heading', { level: 3 })).toHaveText([
      'Vendedor e contactos',
      'Âmbito',
      'Formação do contrato',
      'Produtos',
      'Preços',
      'Encomenda mínima',
      'Pagamento',
      'Entrega',
      'Produtos por medida ou personalizados',
      'Reclamações',
      'Dados pessoais',
      'Lei aplicável e litígios',
      'Entrega destas condições e versão',
    ])
    await expect(empresas.getByRole('heading', { level: 3 })).toHaveText([
      'Pagamento e atraso',
      'Reserva de propriedade',
      'Inspecção e reclamação de defeitos',
      'Devoluções',
      'Responsabilidade',
      'Força maior',
      'Foro',
    ])
    await expect(consumidores.getByRole('heading', { level: 3 })).toHaveText([
      'Informação antes de comprar',
      'Livre resolução: 14 dias',
      'Contratos por telefone',
      'Garantia legal',
      'Pagamentos adicionais',
      'Entrega e risco',
      'Livro de Reclamações e resolução de litígios',
      'Lei aplicável',
    ])
  })

  test('parte comum: vendedor, formação do contrato, preços, mínimo, entrega, medida, reclamações', async ({
    page,
  }) => {
    await mockApi(page)
    await page.goto(CGV)
    const main = page.getByRole('main')
    /** O primeiro parágrafo (ou lista) a seguir ao título da cláusula. */
    const after = (id, tag = 'p') => main.locator(`${id} ~ ${tag}`).first()

    // Identificação completa, a mesma do rodapé (COMPANY): nada de email público.
    const vendedor = after('#vendedor', 'address')
    await expect(vendedor).toContainText(LEGAL_NAME)
    await expect(vendedor).toContainText('Rua da Quintã, n.º 89')
    await expect(vendedor).toContainText(`935 745 663 (${CALL_NOTE})`)
    await expect(vendedor).toContainText('Contacto electrónico: formulário de contacto')

    // Pedido não vinculativo → proposta escrita → aceitação escrita → confirmação em suporte duradouro.
    const passos = after('#formacao-do-contrato', 'ol').locator('li')
    await expect(passos).toHaveCount(3)
    await expect(passos.nth(0)).toContainText('proposta escrita, válida pelo prazo nela indicado')
    await expect(passos.nth(1)).toContainText('aceita a proposta por escrito')
    await expect(passos.nth(2)).toContainText('suporte duradouro')
    await expect(after('#formacao-do-contrato')).toContainText(
      'não vincula o cliente nem a Diomika',
    )
    await expect(main).toContainText('Uma aceitação dada apenas por telefone não fecha o contrato')

    // Preços sob pedido (a empresas sem IVA, a particulares com IVA e portes) e mínimo com IVA.
    await expect(after('#precos')).toContainText('o site não apresenta preços')
    await expect(after('#precos')).toContainText(PRICE_NOTE)
    await expect(after('#encomenda-minima')).toContainText(`A encomenda mínima é de ${MIN_ORDER}.`)

    // Condições comerciais do cliente (ficha, Parte D, item 7; «Até lá»): na proposta escrita.
    await expect(after('#pagamento')).toContainText('indicados na proposta escrita')
    await expect(after('#entrega')).toContainText(
      'zonas de entrega, os prazos e os portes são indicados na proposta escrita',
    )

    // Excepção geral dos produtos por medida (DL 24/2014, art. 17.º, n.º 1, al. c)); ficha, item 6.
    const medida = after('#produtos-por-medida')
    await expect(medida).toContainText('bordado, logótipo ou medida feita a pedido')
    await expect(medida).toContainText('art. 17.º, n.º 1, al. c)')
    await expect(medida).toContainText(
      'Escolher uma cor ou uma medida do catálogo não torna o produto personalizado',
    )

    // Reclamações: Livro de Reclamações Eletrónico e 15 dias úteis; dados pessoais → privacidade.
    const reclamacoes = after('#reclamacoes')
    await expect(
      reclamacoes.getByRole('link', { name: 'Livro de Reclamações Eletrónico' }),
    ).toHaveAttribute('href', 'https://www.livroreclamacoes.pt')
    await expect(reclamacoes).toContainText('15 dias úteis')
    await expect(
      after('#dados-pessoais').getByRole('link', { name: 'Política de Privacidade' }),
    ).toHaveAttribute('href', '/privacidade')
  })

  test('parte para empresas: o que a lei permite dizer, com as ressalvas dos arts. 18.º e 19.º do DL 446/85', async ({
    page,
  }) => {
    await mockApi(page)
    await page.goto(CGV)
    const main = page.getByRole('main')

    const clauses = {
      '#empresas-pagamento': [
        'juros de mora à taxa legal',
        '40 €',
        'Decreto-Lei n.º 62/2013, arts. 4.º e 7.º',
      ],
      '#empresas-reserva-de-propriedade': [
        'propriedade dos bens até receber o pagamento integral',
        'Código Civil, art. 409.º',
      ],
      '#empresas-defeitos': [
        'nos 8 dias seguintes (Código Comercial, art. 471.º)',
        'até 30 dias depois de o comprador os conhecer',
        'dentro de 6 meses a contar da entrega (Código Civil, art. 916.º)',
      ],
      '#empresas-devolucoes': [
        'não existe direito de devolução por arrependimento',
        'por acordo escrito prévio',
        'custos de devolução a cargo do comprador',
      ],
      '#empresas-responsabilidade': [
        'culpa leve limita-se ao valor da encomenda',
        'danos indirectos',
        'danos pessoais nem à morte',
        'dolo ou culpa grave',
        'Decreto-Lei n.º 446/85, art. 18.º',
      ],
      '#empresas-forca-maior': ['força maior'],
      '#empresas-foro': ['tribunal da comarca de Guimarães'],
    }
    for (const [id, phrases] of Object.entries(clauses)) {
      for (const phrase of phrases) {
        await expect(main.locator(`${id} ~ p`).first(), `${id}: ${phrase}`).toContainText(phrase)
      }
    }
  })

  test('parte para consumidores: informação pré-contratual, telefone, garantia, entrega e risco, litígios', async ({
    page,
  }) => {
    await mockApi(page)
    await page.goto(CGV)
    const main = page.getByRole('main')

    const informacao = main.locator('#informacao-pre-contratual ~ ul').first()
    await expect(informacao.locator('li')).toHaveCount(9)
    await expect(informacao).toContainText('o preço total, com IVA, e os portes')
    await expect(informacao).toContainText('a Diomika não está vinculada a nenhum')
    await expect(main).toContainText('art. 4.º, n.º 1, do Decreto-Lei n.º 24/2014')

    const clauses = {
      '#livre-resolucao': [
        'no prazo de 14 dias',
        'arts. 10.º a 13.º',
        'produtos por medida ou personalizados',
      ],
      '#contratos-por-telefone': [
        'identifica-se e indica o fim comercial',
        'art. 5.º, n.º 8',
        'no prazo de 5 dias',
        'art. 6.º',
      ],
      '#garantia': [
        'garantia legal de conformidade de 3 anos a contar da entrega',
        'Decreto-Lei n.º 84/2021, art. 12.º',
        'primeiros 2 anos',
        'art. 13.º',
        'reparação ou à substituição do bem, à redução proporcional do preço ou à resolução do contrato',
      ],
      '#pagamentos-adicionais': [
        'consentimento expresso do consumidor',
        'Lei n.º 24/96, art. 9.º-A',
      ],
      '#entrega-e-risco': [
        'sem demora injustificada e, o mais tardar, 30 dias após a celebração do contrato',
        'art. 11.º, n.º 5',
        'O risco de perda ou de dano dos bens passa para o consumidor',
        'art. 11.º, n.º 12',
      ],
      '#reclamacoes-e-litigios': [
        'Livro de Reclamações Eletrónico',
        TRIAVE,
        'www.triave.pt',
        'valor até 5 000 €',
        'Lei n.º 24/96, art. 14.º, n.º 2',
        'Portal do Consumidor',
      ],
      '#lei-aplicavel-consumidores': [
        'lei portuguesa',
        'normas imperativas de protecção do consumidor',
        'não têm cláusula de foro',
      ],
    }
    for (const [id, phrases] of Object.entries(clauses)) {
      for (const phrase of phrases) {
        await expect(main.locator(`${id} ~ p`).first(), `${id}: ${phrase}`).toContainText(phrase)
      }
    }
    await expect(main).not.toContainText('Foro competente: Portugal')
    // A plataforma europeia de RLL fechou em 20-7-2025 (Reg. 2024/3228): não se liga a ela.
    await expect(page.locator('a[href*="ec.europa.eu/consumers/odr"]')).toHaveCount(0)
  })

  test('formulário-modelo de livre resolução (anexo ao DL 24/2014, partes A e B), preenchido para a Diomika', async ({
    page,
  }) => {
    await mockApi(page)
    await page.goto(CGV)

    // Parte A: a informação sobre o direito de livre resolução.
    const informacao = page.locator('#informacao-livre-resolucao')
    await expect(informacao.getByRole('heading', { level: 4 })).toHaveText(
      'Formulário de informação sobre o direito de livre resolução',
    )
    for (const phrase of [
      'prazo de 14 dias de calendário, sem necessidade de indicar qualquer motivo',
      'a posse física dos bens',
      'a posse física do último bem',
      'declaração inequívoca (por exemplo, carta enviada pelo correio)',
      'Pode utilizar o modelo de formulário de resolução, mas tal não é obrigatório',
      'ser-lhe-ão reembolsados todos os pagamentos efetuados, incluindo os custos de entrega',
      'o mais tardar 14 dias a contar da data em que formos informados',
      'Podemos reter o reembolso até termos recebido os bens devolvidos',
      'Se a proposta nada indicar, suportamo-los nós',
      'Só é responsável pela depreciação dos bens que decorra de uma manipulação que exceda o necessário',
      `${LEGAL_NAME}, Rua da Quintã, n.º 89, 4805-116 Caldas das Taipas, Guimarães; telefone 935 745 663 (${CALL_NOTE})`,
    ]) {
      await expect(informacao, phrase).toContainText(phrase)
    }
    // Sem resolução por via electrónica no sítio: obrigaria a acusar a recepção em 24 h (DL 24/2014,
    // art. 11.º, n.º 4). O formulário de contacto não é canal da livre resolução.
    await expect(informacao).not.toContainText('por via eletrónica')
    await expect(informacao).not.toContainText('24 horas')
    await expect(informacao.locator('a[href="/contacto"]')).toHaveCount(0)

    // Parte B: o modelo de formulário, com o nome e a sede da Diomika.
    const formulario = page.locator('#formulario-livre-resolucao')
    await expect(formulario).toBeVisible()
    await expect(formulario.getByRole('heading', { level: 4 })).toHaveText(
      'Modelo de formulário de livre resolução',
    )
    await expect(formulario).toContainText(
      '(só deve preencher e devolver o presente formulário se quiser resolver o contrato)',
    )
    await expect(formulario.locator('ul.form-lines > li')).toHaveText([
      `Para ${LEGAL_NAME}, Rua da Quintã, n.º 89, 4805-116 Caldas das Taipas, Guimarães:`,
      'Pela presente comunico/comunicamos (*) que resolvo/resolvemos (*) do meu/nosso (*) contrato de compra e venda relativo ao seguinte bem (*)/para a prestação do seguinte serviço (*)',
      'Solicitado em (*)/recebido em (*)',
      'Nome do(s) consumidor(es)',
      'Endereço do(s) consumidor(es)',
      'Assinatura do(s) consumidor(es) (só no caso de o presente formulário ser notificado em papel)',
      'Data',
    ])
    await expect(formulario).toContainText('(*) Riscar o que não interessa.')

    // Sem email público (ficha do cliente, Parte D, item 2): o formulário por carta para a sede e, em
    // alternativa, qualquer outra declaração inequívoca por qualquer meio (DL 24/2014, art. 11.º, n.os 1 e 2:
    // carta, telefone, devolução do bem…), não só por carta. Com COMPANY.email preenchido, o email passa a canal.
    await expect(page.locator('a[href^="mailto:"]')).toHaveCount(0)
    const canais = page.locator('#formulario-livre-resolucao ~ p').first()
    await expect(canais).toHaveText(
      'Envie o formulário por carta para a nossa sede, ou comunique a sua decisão por qualquer outra declaração inequívoca.',
    )
    await expect(canais.getByRole('link')).toHaveCount(0)
    // «Qualquer outra declaração inequívoca» não fica presa à carta: um telefonema ou uma mensagem de
    // WhatsApp também valem, e o pessoal não os pode recusar por a frase parecer só de cartas.
    await expect(page.getByRole('main')).not.toContainText('declaração inequívoca, por carta')
    await expect(page.getByRole('main')).not.toContainText('24 horas')
    await expect(page.getByRole('main')).not.toContainText('assunto «Livre resolução»')
  })

  test('as ligações do início da página levam às partes e ao formulário', async ({ page }) => {
    await mockApi(page)
    await page.goto(CGV)
    const main = page.getByRole('main')

    await main.getByRole('link', { name: 'parte para consumidores' }).first().click()
    await expect(page).toHaveURL(/#parte-consumidores$/)
    await expect(
      main.getByRole('heading', { name: 'Parte para consumidores: vendas a consumidores' }),
    ).toBeInViewport()

    await page.goto(CGV)
    await main.getByRole('link', { name: 'formulário-modelo de livre resolução' }).click()
    await expect(page).toHaveURL(/#formulario-livre-resolucao$/)
    await expect(
      main.getByRole('heading', { name: 'Modelo de formulário de livre resolução' }),
    ).toBeInViewport()
  })

  test('o endereço #formulario-livre-resolucao abre já no formulário', async ({ page }) => {
    await mockApi(page)
    await page.goto(`${CGV}#formulario-livre-resolucao`)

    await expect(
      page.getByRole('heading', { name: 'Modelo de formulário de livre resolução' }),
    ).toBeInViewport()
  })

  test('letra de pelo menos 11 pt e entrelinha de pelo menos 1,15 em todo o texto (DL 446/85, art. 21.º, al. i))', async ({
    page,
  }) => {
    await mockApi(page)
    for (const { url } of PAGES) {
      await page.goto(url)
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()

      const tooSmall = await page.evaluate(() => {
        const MIN_PX = (11 * 96) / 72
        /** @type {string[]} */
        const bad = []
        for (const el of document.querySelectorAll(
          'article.legal-content, article.legal-content *',
        )) {
          const hasText = [...el.childNodes].some(
            (node) => node.nodeType === Node.TEXT_NODE && (node.textContent || '').trim(),
          )
          if (!hasText) continue
          const style = getComputedStyle(el)
          const size = parseFloat(style.fontSize)
          const lineHeight =
            style.lineHeight === 'normal' ? 1.2 * size : parseFloat(style.lineHeight)
          if (size < MIN_PX - 0.01 || lineHeight / size < 1.15 - 0.001) {
            bad.push(
              `${el.tagName} ${size}px / ${lineHeight}px: ${(el.textContent || '').trim().slice(0, 40)}`,
            )
          }
        }
        return bad
      })
      expect(tooSmall, url).toEqual([])
    }
  })

  test('no telemóvel as duas páginas não deslocam na horizontal', async ({ page }) => {
    await mockApi(page)
    await page.setViewportSize({ width: 375, height: 812 })
    for (const { url } of PAGES) {
      await page.goto(url)
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      )
      expect(overflow, url).toBeLessThanOrEqual(0)
    }
  })
})

test.describe('perguntas frequentes', () => {
  const QUESTIONS = [
    'Vendem a particulares?',
    'Porque não há preços no site?',
    'Qual é a encomenda mínima?',
    'Como peço um orçamento? O pedido obriga-me a comprar?',
    'Em quanto tempo respondem?',
    'Quais são os prazos e as zonas de entrega? E os portes?',
    'Como posso pagar?',
    'Posso devolver os artigos?',
    'Que garantia têm os produtos?',
    'Passam faturas com NIF de empresa?',
    'Onde vejo a composição, os cuidados e o fabricante dos produtos?',
    'Fazem personalização? E a devolução?',
    'Como posso reclamar?',
    'Como peço acesso ou apagamento dos meus dados?',
  ]

  test('as 14 perguntas; a resposta abre ao clicar na pergunta', async ({ page }) => {
    await mockApi(page)
    await page.goto(FAQ)

    await expect(page.locator('details > summary')).toHaveText(QUESTIONS)
    const resposta = page
      .locator('details', { hasText: 'Qual é a encomenda mínima?' })
      .locator('.answer')
    await expect(resposta).toBeHidden()
    await page.getByText('Qual é a encomenda mínima?', { exact: true }).click()
    await expect(resposta).toBeVisible()
    await expect(resposta).toHaveText(`A encomenda mínima é de ${MIN_ORDER}.`)
  })

  test('respostas: preço de particulares, pedido não vinculativo, resposta em 1 dia útil, sem email', async ({
    page,
  }) => {
    await mockApi(page)
    await page.goto(FAQ)
    const main = page.getByRole('main')

    await expect(main).toContainText(PRICE_NOTE)
    await expect(main).toContainText(
      'O pedido não o obriga a comprar nem obriga a Diomika a vender',
    )
    await expect(main).toContainText('Respondemos aos pedidos de orçamento no prazo de 1 dia útil')
    await expect(page.locator('a[href^="mailto:"]')).toHaveCount(0)

    // A livre resolução: os mesmos canais das condições, sem o formulário de contacto.
    const devolucoes = page.locator('details', { hasText: 'Posso devolver os artigos?' })
    await expect(devolucoes).toContainText(
      'por carta para a nossa sede, ou comunique a sua decisão por qualquer outra declaração inequívoca',
    )
    await expect(devolucoes).not.toContainText('declaração inequívoca, por carta')
    await expect(devolucoes).not.toContainText('formulário de contacto')
  })

  test('as respostas dizem o mesmo que as condições gerais de venda (Lei 24/96, art. 7.º, n.º 5: o que se promete a um consumidor vincula)', async ({
    page,
  }) => {
    await mockApi(page)
    const normal = (text) => (text ?? '').replace(/[\s\u00a0]+/g, ' ')
    await page.goto(CGV)
    const condicoes = normal(await page.getByRole('main').textContent())
    await page.goto(FAQ)
    const perguntas = normal(await page.getByRole('main').textContent())

    for (const fact of [
      MIN_ORDER,
      PRICE_NOTE,
      'no prazo de 14 dias',
      '3 anos a contar da entrega',
      'primeiros 2 anos',
      'sem demora injustificada e, o mais tardar, 30 dias após a celebração do contrato',
      'por acordo escrito',
      'custos de devolução a cargo do comprador',
      'por carta para a nossa sede, ou comunique a sua decisão por qualquer outra declaração inequívoca',
      'nos 8 dias seguintes',
      'até 30 dias depois de',
      'dentro de 6 meses a contar da entrega',
      '15 dias úteis',
      'art. 17.º, n.º 1, al. c)',
      TRIAVE,
    ]) {
      expect(condicoes, `condições: ${fact}`).toContain(fact)
      expect(perguntas, `perguntas: ${fact}`).toContain(fact)
    }
  })

  test('a ligação «formulário-modelo» da pergunta sobre devoluções leva ao formulário', async ({
    page,
  }) => {
    await mockApi(page)
    await page.goto(FAQ)

    await page.getByText('Posso devolver os artigos?', { exact: true }).click()
    await page.getByRole('link', { name: 'formulário-modelo' }).click()

    await expect(page).toHaveURL(new RegExp(`${CGV}#formulario-livre-resolucao$`))
    // A página nova só monta depois da transição de saída: o scroll espera pela secção.
    await expect(
      page.getByRole('heading', { name: 'Modelo de formulário de livre resolução' }),
    ).toBeInViewport()
  })
})

test.describe('LEGAL-11 e RP-15: o mínimo com IVA e quem compra', () => {
  test('início: lojas, hotelaria e particulares, o mínimo com IVA e o preço a particulares', async ({
    page,
  }) => {
    await mockApi(page)
    await page.goto('/')

    // Linha curta no início (o dono pediu menos legendas); a nota dos preços fica em «Sobre nós», FAQ e condições.
    const nota = page.locator('.hero-note')
    await expect(nota).toContainText('lojas, hotelaria e particulares')
    await expect(nota).toContainText(`pedido mínimo ${MIN_ORDER}`)
  })

  test('sobre nós: a mesma linha no início da página e a nota dos preços', async ({ page }) => {
    await mockApi(page)
    await page.goto('/sobre')

    await expect(page.locator('.hero .hero-note')).toHaveText(SELLS_TO)
    await expect(page.getByRole('main')).toContainText(PRICE_NOTE)
  })

  test('pedido de orçamento e página de produto dizem o mínimo com IVA', async ({
    page,
  }) => {
    await mockApi(page)
    await seedCart(page)

    await page.goto('/carrinho')
    const alerta = page.locator('.page-header .alert-info')
    await expect(alerta).toContainText(`Mínimo de encomenda: ${MIN_ORDER}.`)

    await page.goto('/categoria/almofada/agate')
    const nota = page.locator('.buy-note')
    await expect(nota).toContainText(`Mínimo de encomenda: ${MIN_ORDER}.`)
  })

  test('nenhuma página mostra «500 € + IVA» sem o valor com IVA ao lado', async ({ page }) => {
    await mockApi(page)
    await seedCart(page)
    for (const url of [
      '/',
      '/sobre',
      '/contacto',
      '/categorias',
      '/categoria/almofada',
      '/categoria/almofada/agate',
      '/carrinho',
      '/termos',
      CGV,
      FAQ,
    ]) {
      await page.goto(url)
      await page.waitForLoadState('networkidle')
      const text = (await page.locator('body').innerText()).replace(/\u00a0/g, ' ')
      expect(text.match(/500 ?€ \+ IVA(?! \(615 € com IVA a 23 %\))/g), url).toBeNull()
    }
  })
})

// O custo da chamada (DL 59/2021, art. 4.º) fica só nos blocos de identificação legal: o dono pediu menos legendas.
test('custo da chamada nas condições de venda', async ({ page }) => {
  await mockApi(page)
  await page.goto(CGV)
  await expect(page.locator('main')).toContainText(CALL_NOTE)
})
