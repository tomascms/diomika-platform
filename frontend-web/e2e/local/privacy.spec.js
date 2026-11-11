// @ts-check
// Política de Privacidade (RGPD art. 13.º) e formulário de contacto com telefone opcional
// (auditoria: LEGAL-05, LEGAL-13, LEGAL-16).
//
// Os valores legais estão escritos à letra de propósito: se o texto ou COMPANY mudarem por engano, o
// teste reprova. O banner de cookies entra já com a escolha feita (fixo, em baixo, taparia as ligações).
import { test, expect } from '@playwright/test'
import { mockApi } from './helpers.js'

const LEGAL_NAME = 'DIOMIKA INTERNACIONAL, UNIPESSOAL, LDA'
const CONSENT_KEY = 'diomika_cookie_consent'

/** @param {import('@playwright/test').Page} page */
const chooseCookies = (page) =>
  page.addInitScript(([key]) => localStorage.setItem(key, 'rejected'), [CONSENT_KEY])

test.describe('Política de Privacidade', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page)
    await chooseCookies(page)
    await page.goto('/privacidade')
  })

  test('identifica o responsável sem email: o contacto é o formulário ou a sede', async ({
    page,
  }) => {
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Política de Privacidade')
    const main = page.getByRole('main')
    const responsavel = main.locator('#responsavel')

    await expect(responsavel).toContainText(LEGAL_NAME)
    await expect(responsavel).toContainText('Sociedade unipessoal por quotas')
    await expect(responsavel).toContainText(
      'Sede: Rua da Quintã, n.º 89, 4805-116 Caldas das Taipas, Guimarães',
    )
    await expect(responsavel).toContainText(
      'Matrícula na Conservatória do Registo Comercial e NIPC 508 651 557',
    )
    await expect(responsavel).toContainText('935 745 663')
    await expect(responsavel).toContainText('Não temos encarregado de protecção de dados')
    await expect(
      responsavel.getByRole('link', { name: 'formulário de contacto' }).last(),
    ).toHaveAttribute('href', '/contacto')
    await expect(responsavel).toContainText('escreva-nos para a sede')

    // Decisão do dono (ficha do cliente, Parte D, item 2): sem email público; nunca a caixa do prestador.
    await expect(page.locator('a[href^="mailto:"]')).toHaveCount(0)
    expect(await main.innerText()).not.toMatch(/@/)
    expect(await main.innerText()).not.toMatch(/gmail\.com/i)
  })

  test('tabela finalidade, dados, base legal e prazo', async ({ page }) => {
    const table = page.locator('#finalidades').getByRole('table')
    await expect(table.getByRole('columnheader')).toHaveText([
      'Finalidade',
      'Dados',
      'Base legal',
      'Prazo',
    ])
    const row = (name) =>
      table.getByRole('row').filter({ has: page.getByRole('rowheader', { name, exact: true }) })

    await expect(table.getByRole('rowheader')).toHaveText([
      'Pedido de orçamento',
      'Contacto',
      'Vendas, faturação e arquivo',
      'Correspondência por email, WhatsApp e telefone',
      'Segurança e anti-spam',
      'Medição de audiência (PostHog)',
      'Auditoria do backoffice',
      'Resposta a pedidos de direitos',
    ])

    const orcamento = row('Pedido de orçamento')
    await expect(orcamento).toContainText('telefone (facultativo)')
    await expect(orcamento).toContainText('empresa, NIF e localidade (facultativos)')
    await expect(orcamento).toContainText('como empresa ou como particular')
    await expect(orcamento).toContainText('art. 6.º, n.º 1, al. b)')
    await expect(orcamento).toContainText('24 meses se não houver venda; 10 anos se houver venda')
    await expect(orcamento).toContainText('Código Comercial, art. 40.º')

    await expect(row('Contacto')).toContainText('telefone (facultativo)')
    await expect(row('Contacto')).toContainText('24 meses')
    await expect(row('Vendas, faturação e arquivo')).toContainText('10 anos')
    await expect(row('Vendas, faturação e arquivo')).toContainText('Código do IVA, art. 52.º')
    await expect(row('Segurança e anti-spam')).toContainText('Endereço IP')
    await expect(row('Segurança e anti-spam')).toContainText('art. 6.º, n.º 1, al. f)')
    await expect(row('Segurança e anti-spam')).toContainText('Registos técnicos: ver o ponto 7')
    const posthog = row('Medição de audiência (PostHog)')
    await expect(posthog).toContainText('Consentimento')
    await expect(posthog).toContainText('Lei n.º 41/2004, art. 5.º')
    await expect(posthog).toContainText('localização aproximada calculada a partir do endereço IP')
    // Nada afirmado que o código ou o PostHog não garantam: nem o IP «não guardado», nem que retirar apaga o já guardado.
    await expect(posthog).not.toContainText('não fica guardado')
    await expect(posthog).toContainText(
      'Pelo período de retenção do PostHog (1 ano no plano gratuito). Deixamos de medir quando retirar o consentimento',
    )
    await expect(posthog).not.toContainText('até retirar o consentimento')
    await expect(row('Auditoria do backoffice')).toContainText('12 meses')
    await expect(row('Resposta a pedidos de direitos')).toContainText('art. 6.º, n.º 1, al. c)')

    // Interesse legítimo descrito, dados obrigatórios (art. 13.º, n.º 2, al. e)).
    await expect(page.locator('#interesses')).toContainText('manter o site e a empresa seguros')
    await expect(page.locator('#obrigatorios')).toContainText('o nome e o email são obrigatórios')
    await expect(page.locator('#obrigatorios')).toContainText(
      'O telefone, a empresa, o NIF e a localidade são facultativos',
    )
  })

  test('destinatários: cada fornecedor por empresa e função, quem decide, o local e a base da transferência', async ({
    page,
  }) => {
    const section = page.locator('#destinatarios')
    const table = section.getByRole('table')
    await expect(table.getByRole('columnheader')).toHaveText([
      'Entidade',
      'Função',
      'Quem decide para que os dados servem',
      'Onde ficam os dados',
      'Transferência para fora da União Europeia',
    ])
    await expect(table.getByRole('rowheader')).toHaveText([
      'Supabase',
      'Render (Render Services, Inc.)',
      'GitHub (Microsoft)',
      'Cloudflare',
      'Google (Gmail)',
      'Sentry',
      'Axiom',
      'PostHog',
      'ntfy.sh',
      'Meta (WhatsApp)',
      'Prestador de manutenção do site',
    ])
    const row = (name) =>
      table.getByRole('row').filter({ has: page.getByRole('rowheader', { name, exact: true }) })

    await expect(row('Supabase')).toContainText('Irlanda (União Europeia)')
    await expect(row('Render (Render Services, Inc.)')).toContainText('Frankfurt (União Europeia)')
    await expect(row('GitHub (Microsoft)')).toContainText('EUA')
    for (const name of [
      'GitHub (Microsoft)',
      'Cloudflare',
      'Google (Gmail)',
      'Meta (WhatsApp)',
    ]) {
      // A base, dita em geral: não se afirma que cada fornecedor esteja certificado (não está verificado).
      await expect(row(name)).toContainText(
        'Sim: decisão de adequação UE-EUA (Data Privacy Framework), quando o fornecedor está certificado, ou outras garantias adequadas do art. 46.º do RGPD, como as cláusulas contratuais-tipo da Comissão.',
      )
    }
    for (const name of ['Supabase', 'Render (Render Services, Inc.)', 'Sentry', 'Axiom', 'PostHog']) {
      await expect(row(name)).toContainText(
        'Só se o fornecedor aceder de fora da UE: garantias adequadas do art. 46.º do RGPD, como as cláusulas contratuais-tipo da Comissão.',
      )
    }
    // Quem decide, por linha. A Diomika, nos que são só infra-estrutura; a Meta é responsável pelas mensagens que
    // recebe; a Cloudflare é responsável pelos sinais do Turnstile que usa para o melhorar (política do Turnstile,
    // 4(ii)); na Google o tipo de conta não está confirmado, por isso não se diz só «A Diomika».
    const decides = (name) => row(name).getByRole('cell').nth(1)
    for (const name of [
      'Supabase',
      'Render (Render Services, Inc.)',
      'GitHub (Microsoft)',
      'Sentry',
      'Axiom',
      'PostHog',
      'Prestador de manutenção do site',
    ]) {
      await expect(decides(name)).toHaveText('A Diomika')
    }
    await expect(decides('Cloudflare')).toHaveText(
      'A Diomika, quanto ao alojamento, à rede e à verificação anti-spam. A Cloudflare, quanto a melhorar o Turnstile (política do Turnstile)',
    )
    await expect(decides('Google (Gmail)')).toHaveText(
      'A Diomika, quanto às mensagens que trata. A Google, quanto ao funcionamento e à segurança do serviço de email, segundo os termos da conta',
    )
    await expect(decides('ntfy.sh')).toHaveText('Não aplicável')
    await expect(row('Meta (WhatsApp)').getByRole('cell').nth(1)).toHaveText(
      'A Meta, quanto às mensagens que lhe enviar: é responsável pelo seu tratamento, segundo a sua política. A Diomika, quanto às que recebe',
    )
    await expect(row('Axiom')).toContainText('endereço IP')
    await expect(row('ntfy.sh')).toContainText(
      'não levam endereços IP, nomes nem outros dados pessoais',
    )
    await expect(row('Prestador de manutenção do site')).toContainText('só quando necessário')

    await expect(section).toContainText('Não vendemos os seus dados')
    // O art. 28.º só se afirma depois de assinado o acordo com cada um (LEGAL-06): hoje não há nenhum que o garanta.
    await expect(page.getByRole('main')).not.toContainText('art. 28')
    await expect(page.getByRole('main')).not.toContainText('segundo as nossas instruções')
    await expect(section).toContainText('Autoridade Tributária e Aduaneira')
    // Nenhuma cláusula afirmada em nome dos fornecedores: depende do acordo que cada conta aceitou.
    await expect(page.getByRole('main')).not.toContainText('incluídas nos termos do fornecedor')
    await expect(page.locator('#transferencias')).toContainText(
      'decisão de adequação UE-EUA (Data Privacy Framework; art. 45.º do RGPD), quando o fornecedor está certificado, ou em outras garantias adequadas do art. 46.º do RGPD, como as cláusulas contratuais-tipo da Comissão',
    )
    await expect(page.locator('#transferencias')).toContainText(
      'Pode pedir-nos uma cópia dessas garantias',
    )
  })

  test('prazos, direitos (oposição destacada, retirar o consentimento), CNPD, perfis, segurança e menores', async ({
    page,
  }) => {
    const conservacao = page.locator('#conservacao')
    await expect(conservacao).toContainText('apagadas automaticamente ao fim de 24 meses')
    await expect(conservacao).toContainText('10 anos')
    await expect(conservacao).toContainText(
      'Os registos técnicos e os erros não têm um prazo nosso. No servidor (Render), os registos da aplicação ficam pelo período de retenção do Render e os ficheiros de falhas e de avisos que a aplicação escreve apagam-se sempre que ela reinicia ou é actualizada. No Axiom (registos do servidor) e no Sentry (erros) ficam pelo período de retenção de cada um, que é de 30 dias no plano gratuito.',
    )
    await expect(page.getByRole('main')).not.toContainText('90 dias')
    await expect(conservacao).toContainText(
      'As cópias de segurança diárias da base de dados guardam-se 14 dias, num espaço privado do GitHub, e depois apagam-se sozinhas; o que for apagado da base de dados desaparece das cópias nesse prazo.',
    )
    await expect(conservacao).toContainText('revemos a caixa uma vez por ano')
    await expect(page.getByRole('main')).not.toContainText('interesse comercial legítimo, salvo')

    const direitos = page.locator('#direitos')
    for (const right of [
      'acesso',
      'rectificação',
      'apagamento',
      'limitação do tratamento',
      'portabilidade',
    ]) {
      await expect(direitos).toContainText(right)
    }
    await expect(direitos).toContainText(
      'retirar o consentimento a qualquer momento, sem afectar o tratamento anterior',
    )
    await expect(direitos).toContainText('«Preferências de cookies»')
    await expect(direitos).toContainText('prazo de um mês')
    await expect(direitos).toContainText('gratuito')
    await expect(direitos.getByRole('link', { name: 'formulário de contacto' })).toHaveAttribute(
      'href',
      '/contacto',
    )
    // A oposição (art. 21.º, n.º 4) está à parte, com título próprio e uma moldura.
    const oposicao = page.locator('#oposicao')
    await expect(oposicao.getByRole('heading', { name: 'Direito de oposição' })).toBeVisible()
    await expect(oposicao).toContainText('Pode opor-se a qualquer momento')
    expect(await oposicao.evaluate((el) => getComputedStyle(el).borderTopWidth)).toBe('2px')

    await expect(page.locator('#cnpd').getByRole('link', { name: 'www.cnpd.pt' })).toHaveAttribute(
      'href',
      'https://www.cnpd.pt',
    )
    await expect(page.locator('#decisoes')).toContainText(
      'Não tomamos decisões automatizadas nem definimos perfis',
    )
    await expect(page.locator('#seguranca')).toContainText('72 horas')
    await expect(page.locator('#menores')).toContainText('maiores de 18 anos')
    await expect(
      page.locator('#cookies-alteracoes').getByRole('link', { name: 'Política de Cookies' }),
    ).toHaveAttribute('href', '/cookies')
  })

  test('o botão das preferências de cookies reabre o banner', async ({ page }) => {
    await page
      .locator('#cookies-alteracoes')
      .getByRole('button', { name: 'Abrir as preferências de cookies' })
      .click()
    await expect(page.getByRole('region', { name: 'Consentimento de cookies' })).toBeVisible()
  })

  test('as tabelas cabem na coluna do texto, de 721 a 1280 px', async ({ page }) => {
    for (const width of [721, 800, 1024, 1280]) {
      await page.setViewportSize({ width, height: 900 })
      await page.reload()
      await expect(page.locator('.legal-table').first()).toBeVisible()
      const sticksOut = await page.locator('.legal-table').evaluateAll((tables) =>
        tables.map((el) => {
          const t = el.getBoundingClientRect()
          const column = el.closest('section').getBoundingClientRect()
          return Math.max(t.right - column.right, column.left - t.left)
        }),
      )
      for (const px of sticksOut) {
        expect(px, `a ${width} px uma tabela passa a coluna do texto`).toBeLessThanOrEqual(1)
      }
    }
  })

  test('em ecrãs estreitos as tabelas passam a cartões e a página não rola na horizontal', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.reload()

    await expect(page.locator('.legal-table').first()).toBeVisible()
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true)
    const firstValue = page.locator('#finalidades tbody tr').first().locator('td').first()
    expect(await firstValue.evaluate((el) => getComputedStyle(el).display)).toBe('block')
  })
})

test.describe('Formulário de contacto: telefone e assunto opcionais', () => {
  const TURNSTILE = (url) =>
    url.hostname === 'challenges.cloudflare.com' && url.pathname === '/turnstile/v0/api.js'

  /** Abre /contacto com um Turnstile que dá token e uma API que aceita; devolve o que a loja enviar. */
  async function openContact(page) {
    await mockApi(page)
    await chooseCookies(page)
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
    return sent
  }

  async function fillAndSend(page, phone, subject = 'Acesso aos meus dados') {
    await page.getByLabel('Nome').fill('Ana Silva')
    await page.getByLabel('Email').fill('ana@example.com')
    if (phone) await page.getByLabel('Telefone (opcional)').fill(phone)
    if (subject) await page.getByLabel('Assunto (opcional)').fill(subject)
    await page.getByLabel('Mensagem').fill('Gostaria de saber que dados tratam sobre mim.')
    await page.getByRole('button', { name: 'Enviar mensagem' }).click()
    await expect(page.getByText('Mensagem enviada.')).toBeVisible()
  }

  test('o telefone e o assunto dizem «opcional» e não são obrigatórios; o resto leva «*»', async ({ page }) => {
    await openContact(page)

    for (const label of ['Telefone (opcional)', 'Assunto (opcional)']) {
      await expect(page.getByLabel(label)).toBeVisible()
      await expect(page.getByLabel(label)).not.toHaveAttribute('required', /.*/)
    }
    for (const label of ['Nome', 'Email', 'Mensagem']) {
      await expect(page.getByLabel(label)).toHaveAttribute('required', '')
      await expect(page.locator('label', { hasText: label }).locator('.req')).toHaveText('*')
    }
    await expect(page.locator('.required-note')).toHaveText('Os campos com * são obrigatórios.')
    await expect(page.locator('.privacy-note')).toContainText(
      'Usamos estes dados para lhe responder.',
    )
    await expect(
      page.locator('.privacy-note').getByRole('link', { name: 'Política de Privacidade' }),
    ).toHaveAttribute('href', '/privacidade')
  })

  test('envia-se sem telefone: o navegador deixa seguir e o pedido leva o telefone a null', async ({
    page,
  }) => {
    const sent = await openContact(page)
    await fillAndSend(page, '')

    expect(sent).toHaveLength(1)
    expect(sent[0]).toMatchObject({ nome: 'Ana Silva', email: 'ana@example.com', contacto: null })
  })

  test('com telefone, o pedido leva-o', async ({ page }) => {
    const sent = await openContact(page)
    await fillAndSend(page, ' 912 345 678 ')

    expect(sent[0]).toMatchObject({ contacto: '912 345 678' })
  })

  test('envia-se sem assunto: o navegador deixa seguir (a API passa o assunto vazio a «Sem assunto»)', async ({
    page,
  }) => {
    const sent = await openContact(page)
    await fillAndSend(page, '', '')

    expect(sent).toHaveLength(1)
    expect(sent[0]).toMatchObject({ nome: 'Ana Silva', assunto: '' })
  })
})
