// @ts-check
// Catálogo para imprimir ou guardar em PDF (auditoria: RP-14).
//
// Uma página só com texto (modelos, medidas, cores e EAN, sem preços) e CSS de impressão: o dono manda o catálogo por
// WhatsApp ou email a partir do «Guardar em PDF» do navegador. Sem biblioteca de PDF e sem gerar nada no servidor.
import { test, expect } from '@playwright/test'
import { fixture, mockApi, productPages } from './helpers.js'

test.beforeEach(async ({ page }) => {
  await mockApi(page)
  await page.addInitScript(() => {
    localStorage.setItem('diomika_cookie_consent', 'rejected')
    // O diálogo de impressão não abre nos testes: conta-se a chamada.
    window.__prints = 0
    window.print = () => {
      window.__prints += 1
    }
  })
})

/** Quantas variantes com EAN têm os modelos das fixtures. */
async function eanCount() {
  let total = 0
  for (const { file } of productPages()) {
    const model = await fixture(file)
    total += [].concat(model[model._storefront.product_table]).filter((row) => String(row?.ean ?? '').trim()).length
  }
  return total
}

test.describe('o catálogo todo', () => {
  test('lista as categorias com modelos (as vazias não), cada modelo com os seus EAN', async ({ page }) => {
    await page.goto('/catalogo-imprimir')
    await expect(page.getByRole('heading', { level: 1, name: 'Catálogo Diomika' })).toBeVisible()
    await expect(page).toHaveTitle('Catálogo para imprimir | Diomika')

    // Guarda-Chuva, Passadeira e Regional não têm modelos mostráveis.
    await expect(page.locator('.print-category h2')).toHaveText([
      'Almofada',
      'Assento',
      'Material de Cozinha',
      'Óculos',
      'Protetor de Colchão',
      'Toalhas de Mesa',
    ])
    await expect(page.locator('article.print-model')).toHaveCount(productPages().length)
    await expect(page.locator('.print-barcode')).toHaveCount(await eanCount())
    await expect(page.locator('body')).not.toContainText(/sem descri/i)
    // Sem preços e com a identificação de quem vende.
    await expect(page.locator('.print-head')).toContainText('Sem preços: peça orçamento. Pedido mínimo de 500 € + IVA')
    await expect(page.locator('.print-head address')).toContainText('DIOMIKA INTERNACIONAL, UNIPESSOAL, LDA')
  })

  test('um modelo: especificações, 5 fotos, códigos de barras por ordem de medida e as cores', async ({ page }) => {
    await page.goto('/catalogo-imprimir')
    const foglia = page.locator('article.print-model', { has: page.getByRole('heading', { name: 'Foglia', exact: true }) })

    // A descrição gerada repetia as especificações: só entra a que o cliente escreve.
    await expect(foglia.locator('.print-desc')).toHaveCount(0)
    await expect(foglia.locator('.print-specs dt')).toHaveText(['Composição'])
    await expect(foglia.locator('.print-specs dd')).toHaveText(['100% Poliester'])
    await expect(foglia.locator('.print-table')).toHaveCount(0) // a tabela de medidas e EAN saiu: os códigos de barras trazem o EAN
    await expect(foglia.locator('.print-photos img')).toHaveCount(5)
    await expect(foglia.locator('.print-barcode-measure')).toHaveText(['35x50 cm', '45x45 cm', '60x60 cm'])
    await expect(foglia.locator('.print-barcode svg').nth(0)).toHaveAttribute('aria-label', 'EAN 5606044506574')
    await expect(foglia.locator('.print-barcode svg').nth(2)).toHaveAttribute('aria-label', 'EAN 5606044506734')
    await expect(foglia.locator('.print-colors')).toHaveText(
      'Cores: Azul Ciano(12), Azul Marinho(13), Bege(18), Caqui(21), Vermelho(22)',
    )
  })

  test('a descrição que o cliente escreveu sai no papel', async ({ page }) => {
    const list = 'catalogo/almofada/modelos-catalogo/4bba6298-b2d8-4d80-9303-49118f2bb29c'
    const models = await fixture(list)
    const edited = models.map((m) => (m.nome === 'Foglia' ? { ...m, descricao: 'Almofada em veludo, com enchimento de fibra.' } : m))
    await page.route((url) => url.pathname === `/api/${list}`, (route) => route.fulfill({ json: edited }))
    await page.goto('/catalogo-imprimir?categoria=almofada')

    const foglia = page.locator('article.print-model', { has: page.getByRole('heading', { name: 'Foglia', exact: true }) })
    await expect(foglia.locator('.print-desc')).toHaveText('Almofada em veludo, com enchimento de fibra.')
  })

  test('assento por altura, artigo único sem coluna de medida e uma só cor', async ({ page }) => {
    await page.goto('/catalogo-imprimir')
    const liso = page.locator('article.print-model', { has: page.getByRole('heading', { name: 'Liso', exact: true }) })
    await expect(liso.locator('.print-barcode-measure')).toHaveText(['32mm', '45mm'])
    await expect(liso.locator('.print-colors')).toHaveText('Cor: Sortido(1)')

    const avental = page.locator('article.print-model', { has: page.getByRole('heading', { name: 'Avental Liso', exact: true }) })
    await expect(avental.locator('.print-barcode')).toHaveCount(1)
    await expect(avental.locator('.print-barcode-measure')).toHaveCount(0)
  })
})

test.describe('uma categoria', () => {
  test('?categoria= imprime só essa, e as ligações levam lá', async ({ page }) => {
    await page.goto('/catalogo-imprimir?categoria=assento')

    await expect(page.getByRole('heading', { level: 1, name: 'Catálogo Diomika — Assento' })).toBeVisible()
    await expect(page.locator('.print-category h2')).toHaveText(['Assento'])
    await expect(page.locator('article.print-model')).toHaveCount(5)
    await expect(page.getByRole('link', { name: 'Catálogo completo' })).toHaveAttribute('href', '/catalogo-imprimir')

    await page.goto('/categoria/assento')
    await page.getByRole('link', { name: 'Catálogo desta categoria para imprimir ou guardar em PDF' }).click()
    await expect(page).toHaveURL(/\/catalogo-imprimir\?categoria=assento$/)
  })

  test('uma categoria que não existe (ou sem modelos) diz que não há nada para imprimir', async ({ page }) => {
    await page.goto('/catalogo-imprimir?categoria=nao-existe')
    await expect(page.locator('.print-empty')).toContainText('Não há modelos para imprimir nesta categoria.')
    await expect(page.getByRole('button', { name: 'Imprimir / guardar em PDF' })).toBeDisabled()

    await page.goto('/catalogo-imprimir?categoria=passadeiras')
    await expect(page.locator('.print-empty')).toBeVisible()
  })
})

test.describe('impressão', () => {
  test('o botão abre o diálogo de impressão', async ({ page }) => {
    await page.goto('/catalogo-imprimir')
    await page.getByRole('button', { name: 'Imprimir / guardar em PDF' }).click()
    expect(await page.evaluate(() => window.__prints)).toBe(1)
  })

  test('no papel só sai o catálogo: sem cabeçalho, rodapé, WhatsApp nem botões, e cada categoria numa folha', async ({
    page,
  }) => {
    await page.goto('/catalogo-imprimir')
    await expect(page.locator('article.print-model').first()).toBeVisible()
    // O navegador manda `beforeprint` antes de imprimir; o emulateMedia não o manda.
    await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')))
    await page.emulateMedia({ media: 'print' })

    for (const hidden of ['.app-header', '.app-footer', '.whatsapp-fab', '.breadcrumbs', '.print-toolbar']) {
      await expect(page.locator(hidden).first(), hidden).toBeHidden()
    }
    await expect(page.locator('.print-head')).toBeHidden()
    await expect(page.locator('article.print-model').first()).toBeVisible()
    // Cada página começa numa folha nova e tem no máximo 3 modelos (de uma categoria).
    const breaks = await page
      .locator('.print-page')
      .evaluateAll((pages) => pages.map((p) => getComputedStyle(p).breakBefore))
    expect(breaks.length).toBeGreaterThan(0)
    expect(new Set(breaks)).toEqual(new Set(['page']))
    const sizes = await page.locator('.print-page').evaluateAll((pages) => pages.map((p) => p.querySelectorAll('article.print-model').length))
    expect(Math.max(...sizes)).toBeLessThanOrEqual(3)
    expect(await page.locator('article.print-model').first().evaluate((el) => getComputedStyle(el).breakInside)).toBe('avoid')
  })

  // O CSS de impressão do pedido era global e, depois de a vista do pedido ser carregada (também pelo pré-carregamento
  // em segundo plano), escondia tudo ao imprimir qualquer página: uma folha em branco.
  test('depois de ter estado no pedido, imprimir o catálogo não o esvazia', async ({ page }) => {
    await page.goto('/carrinho')
    await page.getByRole('navigation', { name: 'Principal' }).getByRole('link', { name: 'Catálogo' }).click()
    await page.locator('.shortcuts').getByRole('link', { name: 'Catálogo para imprimir ou guardar em PDF' }).click()
    await expect(page.locator('article.print-model').first()).toBeVisible()
    await page.emulateMedia({ media: 'print' })

    await expect(page.locator('.print-head')).toBeHidden()
    await expect(page.locator('article.print-model').first()).toBeVisible()
    await expect(page.locator('footer')).toBeHidden() // o rodapé do site fica de fora, como no resto do catálogo
  })
})

test.describe('onde se encontra', () => {
  test('liga-se do catálogo e abre por endereço directo', async ({ page }) => {
    await page.goto('/categorias')
    await page.locator('.shortcuts').getByRole('link', { name: 'Catálogo para imprimir ou guardar em PDF' }).click()
    await expect(page).toHaveURL(/\/catalogo-imprimir$/)
  })
})

test('cada folha A4 leva até 3 modelos e o que tem mais atributos encolhe até caber', async ({ page }) => {
  const list = 'catalogo/almofada/modelos-catalogo/4bba6298-b2d8-4d80-9303-49118f2bb29c'
  const models = await fixture(list)
  const long = 'Almofada em veludo de toque macio, enchimento de fibra hipoalergénica e capa removível. '.repeat(6)
  await page.route((url) => url.pathname === `/api/${list}`, (route) =>
    route.fulfill({ json: models.map((m) => ({ ...m, descricao: long })) }),
  )
  await page.goto('/catalogo-imprimir?categoria=almofada')
  await expect(page.locator('article.print-model').first()).toBeVisible()
  // No site é uma página normal; as folhas A4 só se montam ao imprimir.
  await expect(page.locator('.print-sheets')).not.toHaveClass(/is-paper/)
  await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')))
  await expect(page.locator('.print-sheets')).toHaveClass(/is-paper/)
  await expect
    .poll(() =>
      page.evaluate(() =>
        [...document.querySelectorAll('.print-model')].every((box) => {
          const s = getComputedStyle(box)
          const room = box.clientHeight - parseFloat(s.paddingTop) - parseFloat(s.paddingBottom)
          return box.querySelector('.print-fit').getBoundingClientRect().height <= room + 1
        }),
      ),
    )
    .toBe(true)
  for (const sheet of await page.locator('.print-page').all())
    expect(await sheet.locator('article.print-model').count()).toBeLessThanOrEqual(3)
  await page.evaluate(() => window.dispatchEvent(new Event('afterprint')))
  await expect(page.locator('.print-sheets')).not.toHaveClass(/is-paper/)
})
