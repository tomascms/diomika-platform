// @ts-check
// Pedido rápido por EAN (auditoria: RP-14).
//
// A pesquisa do catálogo já encontra por EAN; o pedido rápido pergunta-lhe cada EAN da lista e junta ao pedido a
// mesma linha que a ficha do produto junta. A API simulada responde à pesquisa com os modelos das fixtures que têm
// o EAN, como a API verdadeira. O banner de cookies não aparece (escolha já feita).
import { test, expect } from '@playwright/test'
import { fixture, mockApi, productPages } from './helpers.js'

const FOGLIA_35X50 = '5606044506574'
const FOGLIA_60X60 = '5606044506734'

/** Todos os modelos das fixtures, para a pesquisa por EAN. */
const allModels = () => Promise.all(productPages().map(({ file }) => fixture(file)))

/**
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<string[]>} os EAN pesquisados, ao vivo
 */
async function searchByEan(page) {
  const models = await allModels()
  /** @type {string[]} */
  const searched = []
  await page.route(
    (url) => url.pathname === '/api/catalogo/search',
    (route) => {
      const q = new URL(route.request().url()).searchParams.get('q') ?? ''
      searched.push(q)
      const hits = models
        .filter((m) => [].concat(m[m._storefront.product_table] ?? []).some((row) => String(row.ean).includes(q)))
        .map((m) => ({ model: m, category: m.categories, cover_path: '', _tipo_catalogo: m._tipo_catalogo }))
      return route.fulfill({ json: hits })
    },
  )
  return searched
}

/** O EAN da primeira variante de um modelo das fixtures. */
async function eanOf(name, height) {
  const model = (await allModels()).find((m) => m.nome === name)
  const rows = [].concat(model[model._storefront.product_table])
  return (height ? rows.find((r) => r.altura === height) : rows[0]).ean
}

/** @param {import('@playwright/test').Page} page */
async function openQuickOrder(page, cart = null) {
  await mockApi(page)
  await page.addInitScript(
    ([stored]) => {
      localStorage.setItem('diomika_cookie_consent', 'rejected')
      if (stored) localStorage.setItem('diomika_cart', JSON.stringify(stored))
    },
    [cart],
  )
  const searched = await searchByEan(page)
  await page.goto('/pedido-rapido')
  return searched
}

const lines = (page) => page.getByRole('textbox', { name: /Artigos, um por linha/ })
const submit = (page) => page.getByRole('button', { name: 'Juntar ao pedido' })
const stored = (page) => page.evaluate(() => JSON.parse(localStorage.getItem('diomika_cart') || '[]'))

test.describe('juntar artigos', () => {
  test('uma linha por artigo junta tudo ao pedido, com a cor, o passo e a medida certos', async ({ page }) => {
    const liso = await eanOf('Liso', '32mm')
    const avental = await eanOf('Avental Liso')
    await openQuickOrder(page)

    await lines(page).fill(
      [
        `${FOGLIA_35X50}; 12; 240`, //            cor e quantidade certas
        `${FOGLIA_60X60}; 13; 100`, //            100 não é múltiplo de 12: passa a 108
        `${liso}; 24`, //                         assento de uma só cor: a cor pode faltar
        `${avental};;12`, //                      artigo único: a cor também
      ].join('\n'),
    )
    await submit(page).click()

    const results = page.locator('.result-list li')
    await expect(results).toHaveText([
      'Junto: Foglia · 35x50 cm · Cor 12 (Azul Ciano): 240 un.',
      'Junto: Foglia · 60x60 cm · Cor 13 (Azul Marinho): 108 un. Quantidade ajustada de 100 para 108 un.: vendemos em múltiplos de 12.',
      'Junto: Liso · 32mm · Cor 1 (Sortido): 24 un.',
      'Junto: Avental Liso · Cor 1 (Sortido): 12 un.',
    ])
    await expect(page.locator('.quick-summary')).toContainText('4 artigos juntos ao pedido.')
    await expect(lines(page)).toHaveValue('') // nada ficou por juntar

    const cart = await stored(page)
    expect(cart.map((/** @type {any} */ l) => [l.ean, l.numero_cor, l.quantidade, l.altura ?? null])).toEqual([
      [FOGLIA_35X50, 12, 240, null],
      [FOGLIA_60X60, 13, 108, null],
      [liso, 1, 24, '32mm'],
      [avental, 1, 12, null],
    ])

    // É o pedido de sempre: as linhas, os campos de quantidade e o total.
    await page.getByRole('link', { name: 'Ver pedido' }).click()
    await expect(page).toHaveURL(/\/carrinho$/)
    await expect(page.locator('article.line')).toHaveCount(4)
    await expect(page.getByRole('spinbutton', { name: 'Quantidade de Foglia' }).first()).toHaveValue('240')
    await expect(page.locator('.lines-head .badge-pill')).toHaveText('4 artigos · 384 un.')
  })

  test('a mesma lista outra vez não duplica nada: a linha do pedido é a mesma e fica com a última quantidade', async ({
    page,
  }) => {
    await openQuickOrder(page)
    await lines(page).fill(`${FOGLIA_35X50}; 12; 240`)
    await submit(page).click()
    await expect(page.locator('.quick-summary')).toBeVisible()
    await lines(page).fill(`${FOGLIA_35X50}; 12; 60`)
    await submit(page).click()
    await expect(page.locator('.result-list li')).toHaveText(['Junto: Foglia · 35x50 cm · Cor 12 (Azul Ciano): 60 un.'])

    const cart = await stored(page)
    expect(cart).toHaveLength(1)
    expect(cart[0].quantidade).toBe(60)
  })

  test('pede cada EAN uma só vez, mesmo que apareça em várias cores', async ({ page }) => {
    const searched = await openQuickOrder(page)
    await lines(page).fill([`${FOGLIA_35X50}; 12; 12`, `${FOGLIA_35X50}; 13; 12`, `${FOGLIA_35X50}; 18; 12`].join('\n'))
    await submit(page).click()

    await expect(page.locator('.result-list li.is-ok')).toHaveCount(3)
    expect(searched).toEqual([FOGLIA_35X50])
  })
})

test.describe('o que não se pode juntar', () => {
  test('cada linha má diz porquê e fica no campo para corrigir; as boas juntam-se', async ({ page }) => {
    await openQuickOrder(page)
    await lines(page).fill(
      [
        `${FOGLIA_35X50}; 12; 24`, //     boa
        '5606044599999; 1; 12', //        EAN que não existe
        `${FOGLIA_35X50}; 99; 12`, //     cor que não existe
        `${FOGLIA_60X60}; 12`, //         Foglia tem 5 cores: falta a cor
        `${FOGLIA_60X60}; 12; 0`, //      quantidade inválida
        'não é um EAN; 1; 12', //         formato
      ].join('\n'),
    )
    await submit(page).click()

    const results = page.locator('.result-list li')
    await expect(results).toHaveText([
      'Junto: Foglia · 35x50 cm · Cor 12 (Azul Ciano): 24 un.',
      'Linha 2, não junta: O EAN 5606044599999 não existe no catálogo.',
      'Linha 3, não junta: Foglia: a cor 99 não existe. As cores são 12, 13, 18, 21, 22.',
      'Linha 4, não junta: Foglia: indique a cor. As cores são 12, 13, 18, 21, 22.',
      'Linha 5, não junta: A quantidade é um número inteiro (por exemplo, 240).',
      'Linha 6, não junta: O EAN tem 13 dígitos.',
    ])
    await expect(page.locator('.quick-summary')).toContainText('1 artigo junto ao pedido.')
    await expect(page.locator('.alert-error')).toContainText('5 linhas não foram juntas: ficam no campo acima, para corrigir.')
    await expect(lines(page)).toHaveValue(
      [`5606044599999; 1; 12`, `${FOGLIA_35X50}; 99; 12`, `${FOGLIA_60X60}; 12`, `${FOGLIA_60X60}; 12; 0`, 'não é um EAN; 1; 12'].join('\n'),
    )
    expect(await stored(page)).toHaveLength(1)

    // Corrige as duas que sabe corrigir e tenta de novo: juntam-se, e a que já estava no pedido fica como estava.
    await lines(page).fill([`${FOGLIA_35X50}; 13; 12`, `${FOGLIA_60X60}; 12; 12`].join('\n'))
    await submit(page).click()
    await expect(page.locator('.quick-summary')).toContainText('2 artigos juntos ao pedido.')
    expect((await stored(page)).map((/** @type {any} */ l) => [l.ean, l.numero_cor])).toEqual([
      [FOGLIA_35X50, 12],
      [FOGLIA_35X50, 13],
      [FOGLIA_60X60, 12],
    ])
  })

  test('um pedido com 50 artigos não aceita o 51.º (a API recusa mais de 50 linhas)', async ({ page }) => {
    const full = Array.from({ length: 50 }, (_, n) => ({
      ean: `56060440${String(n).padStart(5, '0')}`,
      numero_cor: 1,
      quantidade: 12,
      modeloNome: `Modelo ${n}`,
      dimensoes: '',
      corNome: 'Sortido',
      carrinhoStep: 12,
      carrinhoMin: 12,
    }))
    await openQuickOrder(page, full)
    await lines(page).fill(`${FOGLIA_35X50}; 12; 12`)
    await submit(page).click()

    await expect(page.locator('.result-list li')).toHaveText([
      'Linha 1, não junta: O pedido tem, no máximo, 50 artigos.',
    ])
    expect(await stored(page)).toHaveLength(50)
  })

  test('com o catálogo sem responder, diz-o e não perde a lista', async ({ page }) => {
    await openQuickOrder(page)
    await page.route((url) => url.pathname === '/api/catalogo/search', (route) => route.fulfill({ status: 500, json: {} }))
    await lines(page).fill(`${FOGLIA_35X50}; 12; 24`)
    await submit(page).click()

    await expect(page.locator('.result-list li')).toHaveText([
      'Linha 1, não junta: Não foi possível consultar o catálogo agora. Tente de novo daqui a pouco.',
    ])
    await expect(lines(page)).toHaveValue(`${FOGLIA_35X50}; 12; 24`)
    expect(await stored(page)).toEqual([])
  })

  test('sem texto o botão não faz nada', async ({ page }) => {
    await openQuickOrder(page)
    await expect(submit(page)).toBeDisabled()
    await lines(page).fill('   \n  ')
    await expect(submit(page)).toBeDisabled()
  })
})

test.describe('onde se encontra', () => {
  test('liga-se do pedido e do catálogo, e abre por endereço directo', async ({ page }) => {
    await openQuickOrder(page, [
      { ean: FOGLIA_35X50, numero_cor: 12, quantidade: 12, modeloNome: 'Foglia', dimensoes: '35x50', corNome: 'Azul Ciano', carrinhoStep: 12, carrinhoMin: 12 },
    ])
    await expect(page.getByRole('heading', { level: 1, name: 'Pedido rápido por EAN' })).toBeVisible()
    await expect(page).toHaveTitle('Pedido rápido por EAN | Diomika')

    await page.goto('/carrinho')
    await page.locator('.lines-head').getByRole('link', { name: 'Pedido rápido por EAN' }).click()
    await expect(page).toHaveURL(/\/pedido-rapido$/)

    await page.goto('/categorias')
    await page.locator('.shortcuts').getByRole('link', { name: 'Pedido rápido por EAN' }).click()
    await expect(page).toHaveURL(/\/pedido-rapido$/)
  })
})
