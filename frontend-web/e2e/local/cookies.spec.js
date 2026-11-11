// @ts-check
// Consentimento de cookies: dar, retirar, voltar a perguntar, e o PostHog que só corre com ele
// (auditoria: LEGAL-07; RGPD art. 7.º/3: retirar o consentimento tão fácil como dá-lo).
//
// O PostHog do harness leva uma chave falsa (playwright.config.js): `trackPosthog` (helpers.js) responde-lhe e conta
// os pedidos que o browser lhe faz, venham de onde vierem (fila de eventos, pageleave, SPA, recarregar).
import { test, expect } from '@playwright/test'
import { CONSENT_VERSION } from '../../src/lib/consent.js'
import { mockApi, trackPosthog } from './helpers.js'

const CONSENT_KEY = 'diomika_cookie_consent'
const BANNER = { name: 'Consentimento de cookies' }
const PREFERENCES = { name: 'Preferências de cookies' }

/** Chaves de localStorage e sessionStorage que cumprem `pattern`. */
const storageKeys = (page, pattern) =>
  page.evaluate(
    (source) =>
      [...Object.keys(localStorage), ...Object.keys(sessionStorage)].filter((key) =>
        new RegExp(source).test(key),
      ),
    pattern.source,
  )

const storedChoice = (page) =>
  page.evaluate((key) => JSON.parse(localStorage.getItem(key) || 'null'), CONSENT_KEY)

const footerPreferences = (page) => page.getByRole('contentinfo').getByRole('button', PREFERENCES)

test('sem escolha o PostHog não arranca; «Aceitar» arranca-o, com os dois botões ao mesmo nível', async ({
  page,
}) => {
  await mockApi(page)
  const posthog = await trackPosthog(page)
  // A biblioteca nem sequer se descarrega sem consentimento (é um ficheiro à parte, carregado a pedido).
  const library = []
  page.on('request', (request) => {
    if (/\/assets\/posthog-[^/]*\.js$/.test(request.url())) library.push(request.url())
  })
  await page.goto('/')

  const banner = page.getByRole('region', BANNER)
  await expect(banner).toBeVisible()
  expect(posthog).toEqual([])
  expect(library).toEqual([])
  expect(await storageKeys(page, /^_*ph_/)).toEqual([])

  // Recusar e aceitar custam o mesmo: dois botões lado a lado, do mesmo tamanho.
  const [recusar, aceitar] = await Promise.all([
    banner.getByRole('button', { name: 'Recusar' }).boundingBox(),
    banner.getByRole('button', { name: 'Aceitar' }).boundingBox(),
  ])
  expect(Math.abs((recusar?.height ?? 0) - (aceitar?.height ?? -1))).toBeLessThan(2)
  expect(Math.abs((recusar?.y ?? 0) - (aceitar?.y ?? -1))).toBeLessThan(2)

  await banner.getByRole('button', { name: 'Aceitar' }).click()
  await expect(banner).toBeHidden()
  await expect.poll(() => posthog.some((request) => request.startsWith('POST /e/'))).toBe(true)
  expect(library).toHaveLength(1)

  // A escolha fica com estado, versão e data (prova do consentimento, art. 7.º/1).
  const choice = await storedChoice(page)
  expect(choice).toMatchObject({ state: 'accepted', version: expect.any(String) })
  expect(Date.now() - Date.parse(choice.date)).toBeLessThan(60_000)
})

test('retirar o consentimento: ligação permanente no rodapé e um clique em «Recusar»; depois, 0 pedidos ao PostHog', async ({
  page,
}) => {
  await mockApi(page)
  const posthog = await trackPosthog(page)
  await page.goto('/')

  const banner = page.getByRole('region', BANNER)
  await banner.getByRole('button', { name: 'Aceitar' }).click()
  await expect.poll(() => posthog.some((request) => request.startsWith('POST /e/'))).toBe(true)
  expect(await storageKeys(page, /^ph_/)).not.toEqual([]) // o PostHog guardou chaves no dispositivo

  // Uma mudança de página mesmo antes de retirar: o PostHog por omissão põe o evento numa fila que só a
  // envia 3 s depois, ou seja, depois da retirada (sem o `request_batching: false` este teste reprova).
  await page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Sobre nós' }).click()
  await expect(page).toHaveURL(/\/sobre$/)

  // Retirar: a ligação do rodapé (em todas as páginas) reabre o banner e «Recusar» é um clique.
  await footerPreferences(page).click()
  await expect(banner).toBeVisible()
  await expect(banner).toContainText('aceitou')
  const before = posthog.length
  await banner.getByRole('button', { name: 'Recusar' }).click()
  await expect(banner).toBeHidden()
  // O que o PostHog guardou para medir foi apagado logo ali; fica a marca que lembra a recusa (política de cookies).
  expect(await storageKeys(page, /^ph_/)).toEqual([])
  expect(await storageKeys(page, /^__ph_opt_in_out_/)).toHaveLength(1)

  // A partir daqui nada sai: nem o que ficasse em fila, nem a mudança de página, nem o recarregamento.
  await page.waitForTimeout(4000)
  await page.getByRole('contentinfo').getByRole('link', { name: 'Contacto', exact: true }).click()
  await expect(page).toHaveURL(/\/contacto$/)
  expect(posthog).toHaveLength(before)

  await page.reload()
  await expect(page.getByRole('heading', { level: 1, name: 'Contacto' })).toBeVisible()
  await expect(banner).toBeHidden() // a recusa vale: não pergunta de novo
  await page.waitForTimeout(1000)
  expect(posthog).toHaveLength(before)

  // Depois de recarregar continua assim, e a recusa ficou registada.
  expect(await storageKeys(page, /^ph_/)).toEqual([])
  expect(await page.evaluate(() => window.__diomikaPosthog)).toBeUndefined()
  expect(await storedChoice(page)).toMatchObject({ state: 'rejected' })
})

test('depois de retirar, voltar a aceitar põe o PostHog a funcionar outra vez (na mesma página)', async ({
  page,
}) => {
  await mockApi(page)
  const posthog = await trackPosthog(page)
  await page.goto('/')

  const banner = page.getByRole('region', BANNER)
  await banner.getByRole('button', { name: 'Aceitar' }).click()
  await expect.poll(() => posthog.some((request) => request.startsWith('POST /e/'))).toBe(true)
  await footerPreferences(page).click()
  await banner.getByRole('button', { name: 'Recusar' }).click()
  await expect(banner).toBeHidden()
  const refused = posthog.length

  await footerPreferences(page).click()
  await expect(banner).toContainText('recusou')
  await banner.getByRole('button', { name: 'Aceitar' }).click()
  await expect.poll(() => posthog.length).toBeGreaterThan(refused)
  expect(await storedChoice(page)).toMatchObject({ state: 'accepted' })
})

test('depois de retirar e recarregar a página, voltar a aceitar também põe o PostHog a funcionar', async ({
  page,
}) => {
  await mockApi(page)
  const posthog = await trackPosthog(page)
  await page.goto('/')

  const banner = page.getByRole('region', BANNER)
  await banner.getByRole('button', { name: 'Aceitar' }).click()
  await expect.poll(() => posthog.some((request) => request.startsWith('POST /e/'))).toBe(true)
  await footerPreferences(page).click()
  await banner.getByRole('button', { name: 'Recusar' }).click()
  await expect(banner).toBeHidden()
  await page.reload()
  await expect(footerPreferences(page)).toBeVisible()
  const refused = posthog.length

  // O PostHog guardou a marca de recusa; ao aceitar de novo, numa página nova, tem de a levantar.
  await footerPreferences(page).click()
  await expect(banner).toContainText('recusou')
  await banner.getByRole('button', { name: 'Aceitar' }).click()
  await expect.poll(() => posthog.length).toBeGreaterThan(refused)
  expect(await storageKeys(page, /^ph_/)).not.toEqual([])
  expect(await storedChoice(page)).toMatchObject({ state: 'accepted' })
  // A marca de recusa não desaparece ao voltar a aceitar (a política de cookies diz que fica até limpar o site).
  expect(await storageKeys(page, /^__ph_opt_in_out_/)).toHaveLength(1)
})

test('recusar sem ter aceitado nesta página (consentimento de uma visita anterior) apaga as chaves do PostHog', async ({
  page,
}) => {
  await mockApi(page)
  const posthog = await trackPosthog(page)
  // Uma visita anterior aceitou e o PostHog deixou chaves; hoje a escolha já expirou.
  await page.addInitScript(
    ([key]) => {
      if (sessionStorage.getItem('e2e-seeded')) return
      sessionStorage.setItem('e2e-seeded', '1')
      localStorage.setItem('ph_phc_e2e_chave_falsa_posthog', '{"distinct_id":"antigo"}')
      localStorage.setItem(
        key,
        JSON.stringify({ state: 'accepted', version: 'antiga', date: '2020-01-01T00:00:00.000Z' }),
      )
    },
    [CONSENT_KEY],
  )
  await page.goto('/')

  const banner = page.getByRole('region', BANNER)
  await expect(banner).toBeVisible() // outra versão: pergunta-se de novo
  expect(posthog).toEqual([]) // e o PostHog não arranca com um consentimento que já não vale
  expect(await storageKeys(page, /^ph_/)).toEqual([]) // nem ficam identificadores antigos

  await banner.getByRole('button', { name: 'Recusar' }).click()
  await page.waitForTimeout(500)
  expect(posthog).toEqual([])
})

test.describe('valores antigos da escolha', () => {
  const OLD = {
    'só texto «accepted» (sem data nem versão)': 'accepted',
    'versão antiga': JSON.stringify({
      state: 'accepted',
      version: 'antiga',
      date: new Date().toISOString(),
    }),
    'mais de 12 meses': JSON.stringify({
      state: 'accepted',
      version: CONSENT_VERSION,
      date: '2025-01-01T00:00:00.000Z',
    }),
  }
  for (const [name, value] of Object.entries(OLD)) {
    test(`${name}: pergunta de novo e o PostHog não arranca`, async ({ page }) => {
      await mockApi(page)
      const posthog = await trackPosthog(page)
      await page.addInitScript(([key, v]) => localStorage.setItem(key, v), [CONSENT_KEY, value])
      await page.goto('/')

      await expect(page.getByRole('region', BANNER)).toBeVisible()
      await page.waitForTimeout(500)
      expect(posthog).toEqual([])
    })
  }

  test('uma recusa guardada em texto, como antes, continua a valer', async ({ page }) => {
    await mockApi(page)
    const posthog = await trackPosthog(page)
    await page.addInitScript(([key]) => localStorage.setItem(key, 'rejected'), [CONSENT_KEY])
    await page.goto('/')

    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await expect(page.getByRole('region', BANNER)).toHaveCount(0)
    expect(posthog).toEqual([])
  })
})

test.describe('«Preferências de cookies» no rodapé de todas as páginas', () => {
  for (const url of [
    '/',
    '/categoria/almofada/agate',
    '/carrinho',
    '/contacto',
    '/privacidade',
    '/cookies',
    '/rota-que-nao-existe',
  ]) {
    test(url, async ({ page }) => {
      await mockApi(page)
      // Já com escolha feita: o banner (fixo, em baixo) não tapa o rodapé.
      await page.addInitScript(([key]) => localStorage.setItem(key, 'rejected'), [CONSENT_KEY])
      await page.goto(url)

      const preferences = footerPreferences(page)
      await expect(preferences).toBeVisible()
      await preferences.click()
      await expect(page.getByRole('region', BANNER)).toBeVisible()
    })
  }
})

test('o banner reaberto leva o foco, o Escape fecha-o sem mudar a escolha e o foco volta ao rodapé', async ({
  page,
}) => {
  await mockApi(page)
  await page.addInitScript(([key]) => localStorage.setItem(key, 'rejected'), [CONSENT_KEY])
  await page.goto('/sobre')

  const banner = page.getByRole('region', BANNER)
  await expect(banner).toHaveCount(0)
  await footerPreferences(page).click()
  await expect(banner).toBeFocused()
  await expect(banner).toContainText('recusou')

  await page.keyboard.press('Escape')
  await expect(banner).toBeHidden()
  await expect(footerPreferences(page)).toBeFocused()
  expect(await page.evaluate((key) => localStorage.getItem(key), CONSENT_KEY)).toBe('rejected')

  // Ou com o botão «Fechar», que só existe quando se reabre.
  await footerPreferences(page).click()
  await banner.getByRole('button', { name: 'Fechar' }).click()
  await expect(banner).toBeHidden()
})

test.describe('Política de Cookies', () => {
  test('a tabela diz nome, tipo, finalidade, categoria, duração e fornecedor de cada item', async ({
    page,
  }) => {
    await mockApi(page)
    await page.addInitScript(([key]) => localStorage.setItem(key, 'rejected'), [CONSENT_KEY])
    await page.goto('/cookies')

    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Política de Cookies')
    const table = page.getByRole('table')
    await expect(table.getByRole('columnheader')).toHaveText([
      'Nome e tipo',
      'Finalidade',
      'Categoria',
      'Duração',
      'Fornecedor',
    ])
    const row = (name) => table.getByRole('row').filter({ hasText: name })

    await expect(row('diomika_cart')).toContainText('localStorage')
    await expect(row('diomika_cart')).toContainText('Necessário')
    await expect(row('diomika_cookie_consent')).toContainText('12 meses')
    await expect(row('diomika_quote_form_draft')).toContainText('Funcional')
    await expect(row('diomika_quote_form_draft')).toContainText(
      'Não guarda o nome, o email nem o telefone',
    )
    for (const name of [
      'diomika-contact-idempotency',
      'diomika-orcamento-idempotency',
      'diomika-origem',
      'diomika_cats_v6',
      'diomika_cat_models_v2',
      'diomika_signed_v5',
    ]) {
      await expect(row(name)).toContainText('sessionStorage')
    }
    await expect(row('Cloudflare Turnstile')).toContainText('challenges.cloudflare.com')
    await expect(row('Cloudflare Turnstile')).toContainText('Necessário (segurança)')
    const posthogKeys = row('ph_<chave>_posthog')
    await expect(posthogKeys).toContainText('Analytics')
    await expect(posthogKeys).toContainText('PostHog (União Europeia)')
    await expect(posthogKeys).toContainText('Só com o seu consentimento')
    await expect(posthogKeys).toContainText(
      'Até recusar; se a escolha expirar (12 meses), apagam-se na visita seguinte. As da sessão acabam com ela.',
    )
    // A marca de recusa não acaba com a recusa: fica (valor 0 ao recusar, 1 se voltar a aceitar) até limpar o site.
    const optOutMark = row('__ph_opt_in_out_<chave>')
    await expect(optOutMark).toContainText('localStorage')
    await expect(optOutMark).toContainText('Necessário')
    await expect(optOutMark).toContainText('Só existe depois de recusar')
    await expect(optOutMark).toContainText(
      'Fica depois de recusar, mesmo que volte a aceitar, até limpar os dados do site',
    )
    await expect(posthogKeys).not.toContainText('__ph_opt_in_out_')

    // Os cookies da rede da Cloudflare: o que são, sem dizer quem os controla.
    const tabela = page.locator('#tabela')
    await expect(tabela).toContainText(
      'A Cloudflare, que serve o site, pode gravar cookies técnicos de segurança da sua rede. São estritamente necessários.',
    )
    await expect(tabela).not.toContainText('controlamos')
  })

  test('explica como gerir: «Preferências de cookies», recusar custa o mesmo, o que acontece e as ligações dos fornecedores', async ({
    page,
  }) => {
    await mockApi(page)
    await page.addInitScript(([key]) => localStorage.setItem(key, 'rejected'), [CONSENT_KEY])
    await page.goto('/cookies')

    const gerir = page.locator('#gerir')
    await expect(gerir).toContainText('«Preferências de cookies»')
    await expect(gerir).toContainText('recusar custa o mesmo clique que aceitar')
    await expect(gerir).toContainText('o PostHog nunca é carregado')
    await expect(gerir).toContainText(
      'apagamos do seu dispositivo o que ele guardou para medir; fica apenas uma marca a lembrar que recusou',
    )
    await expect(gerir).toContainText('12 meses')
    // Já não manda «limpar os dados do site ou contactar-nos» como único caminho.
    const main = page.getByRole('main')
    await expect(main).not.toContainText('contacte-nos')

    await expect(
      main.getByRole('link', { name: /política de privacidade do Turnstile/ }),
    ).toHaveAttribute('href', 'https://www.cloudflare.com/turnstile-privacy-policy/')
    await expect(main.getByRole('link', { name: 'posthog.com/privacy' })).toHaveAttribute(
      'href',
      'https://posthog.com/privacy',
    )
    await expect(main).toContainText('DIOMIKA INTERNACIONAL, UNIPESSOAL, LDA')

    // O botão da própria página reabre o banner, como a ligação do rodapé.
    await gerir.getByRole('button', { name: 'Abrir as preferências de cookies' }).click()
    await expect(page.getByRole('region', BANNER)).toBeVisible()
  })

  test('cada chave que o site escreve no navegador, de uma ponta à outra, consta da tabela', async ({
    page,
  }) => {
    await mockApi(page)
    await trackPosthog(page)
    // Turnstile que dá token (o formulário segue) e uma API que recusa (a chave de idempotência só se apaga ao enviar).
    await page.route(
      (url) =>
        url.hostname === 'challenges.cloudflare.com' && url.pathname === '/turnstile/v0/api.js',
      (route) =>
        route.fulfill({
          contentType: 'text/javascript',
          body: "window.turnstile = { render: (el, options) => { options.callback('token-e2e'); return 'e2e' }, reset() {}, remove() {} }",
        }),
    )
    await page.route(
      (url) => url.pathname === '/api/contacto',
      (route) => route.fulfill({ status: 500, json: { detail: 'e2e: a API recusa' } }),
    )

    // Percorre o que escreve no navegador: o banner, o catálogo, o pedido, o rascunho e um formulário.
    await page.goto('/')
    await page.getByRole('region', BANNER).getByRole('button', { name: 'Aceitar' }).click()
    await page.goto('/categoria/almofada')
    await page.goto('/categoria/almofada/agate')
    await page.getByRole('button', { name: 'Adicionar ao pedido' }).click()
    await page.goto('/carrinho')
    await page.getByLabel('Observações').fill('Entrega em duas fases')
    await page.goto('/contacto')
    await page.getByLabel('Nome').fill('Ana Silva')
    await page.getByLabel('Email').fill('ana@example.com')
    await page.getByLabel('Assunto').fill('Pedido de informação')
    await page.getByLabel('Mensagem').fill('Gostaria de saber mais sobre as almofadas.')
    await page.getByRole('button', { name: 'Enviar mensagem' }).click()
    await expect(page.getByRole('alert').filter({ hasText: 'e2e: a API recusa' })).toBeVisible()

    const written = await storageKeys(page, /./)
    // O teste mexeu mesmo em tudo isto (senão passava por não ter visto nada).
    for (const key of [
      'diomika_cookie_consent',
      'diomika_cart',
      'diomika_quote_form_draft',
      'diomika-contact-idempotency',
      'diomika_cats_v6',
    ]) {
      expect(written, `o site não escreveu ${key}`).toContain(key)
    }
    expect(written.some((key) => key.startsWith('ph_'))).toBe(true)

    // A tabela lista nomes exactos e os padrões do PostHog (`ph_<chave>_*`).
    await page.goto('/cookies')
    const listed = await page.locator('.legal-table code').allTextContents()
    const pattern = (name) =>
      new RegExp(
        `^${name
          .replace(/[.+?^${}()|[\]\\]/g, '\\$&')
          .replace('<chave>', '.+')
          .replace('*', '.*')}$`,
      )
    const unlisted = written.filter((key) => !listed.some((name) => pattern(name).test(key)))
    expect(unlisted, 'chaves do navegador que a política de cookies não lista').toEqual([])
  })

  test('a tabela cabe na coluna do texto, de 721 a 1280 px', async ({ page }) => {
    await mockApi(page)
    await page.addInitScript(([key]) => localStorage.setItem(key, 'rejected'), [CONSENT_KEY])
    for (const width of [721, 800, 1024, 1280]) {
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/cookies')
      const table = page.locator('#tabela .legal-table')
      await expect(table).toBeVisible()
      const sticksOut = await table.evaluate((el) => {
        const t = el.getBoundingClientRect()
        const column = el.closest('section').getBoundingClientRect()
        return { right: t.right - column.right, left: column.left - t.left }
      })
      expect(
        sticksOut.right,
        `a ${width} px a tabela passa a coluna na direita`,
      ).toBeLessThanOrEqual(1)
      expect(
        sticksOut.left,
        `a ${width} px a tabela passa a coluna na esquerda`,
      ).toBeLessThanOrEqual(1)
    }
  })

  test('em ecrãs estreitos a tabela passa a cartões e a página não rola na horizontal', async ({
    page,
  }) => {
    await mockApi(page)
    await page.addInitScript(([key]) => localStorage.setItem(key, 'rejected'), [CONSENT_KEY])
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/cookies')

    await expect(page.locator('.legal-table tbody tr').first()).toBeVisible()
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true)
    // Cada valor traz o nome da coluna: o cabeçalho esconde-se e a linha passa a cartão.
    const firstValue = page.locator('.legal-table tbody tr').first().locator('td').first()
    expect(await firstValue.evaluate((el) => getComputedStyle(el).display)).toBe('block')
    expect(await firstValue.evaluate((el) => getComputedStyle(el, '::before').content)).toBe(
      '"Finalidade"',
    )
  })
})
