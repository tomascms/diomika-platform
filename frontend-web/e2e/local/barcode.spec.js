// @ts-check
// Código de barras em todos os produtos (auditoria: FE-10, SEO-07).
//
// A BD guarda em `barcode_url` o URL assinado que o Storage deu quando o código foi gerado, e esse já expirou: as
// fixtures são cópias reais e 24 dos 26 modelos o têm assim (só as duas almofadas têm o URL público). O Storage recusa
// o assinado com 400 (`InvalidJWT`) e abre o público (`/object/public/…`). Aqui faz-se o mesmo, e o teste passa por
// cada variante de cada modelo: o artigo único (Material de Cozinha, Óculos) mostrava a imagem partida, porque a ficha
// lia o URL das opções do selector e só o ramo das variantes as corrigia.
import { Buffer } from 'node:buffer'
import { test, expect } from '@playwright/test'
import { mockApi, productPages } from './helpers.js'

// PNG de 1×1: basta para o navegador o dar como carregado.
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
  'base64',
)
const STORAGE = 'https://your-project-ref.supabase.co/storage/v1/object'

// Toalha PVC 140x250: os dados não têm imagem do código de barras (a ficha mostra o EAN em texto).
const WITHOUT_IMAGE = new Set(['5606044500688'])

/**
 * O Storage como é: o URL assinado expirado dá 400, o público dá a imagem.
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<string[]>} os URLs assinados que a página pediu, ao vivo
 */
async function storage(page) {
  /** @type {string[]} */
  const signed = []
  await page.route(
    (url) => url.pathname.startsWith('/storage/v1/object/'),
    (route) => {
      const url = route.request().url()
      if (url.includes('/object/sign/')) {
        signed.push(url)
        return route.fulfill({ status: 400, contentType: 'application/json', body: '{"error":"InvalidJWT"}' })
      }
      return route.fulfill({ contentType: 'image/png', body: PNG })
    },
  )
  return signed
}

test.describe('a imagem do código de barras carrega em todos os modelos', () => {
  for (const { url, name, category } of productPages()) {
    test(`${name} (${category})`, async ({ page }) => {
      await mockApi(page)
      await page.addInitScript(() => localStorage.setItem('diomika_cookie_consent', 'rejected'))
      const signed = await storage(page)
      await page.goto(url)
      await expect(page.locator('.ean-line')).toBeVisible()

      // Uma só opção (artigo único) ou uma por medida/altura: o código de barras de cada uma.
      const chips = page.locator('.picker-chip')
      const options = Math.max(await chips.count(), 1)
      for (let i = 0; i < options; i += 1) {
        if ((await chips.count()) > 0) await chips.nth(i).click()
        const ean = (await page.locator('.ean-line').innerText()).replace('EAN', '').trim()
        const image = page.locator('img.barcode-img')

        if (WITHOUT_IMAGE.has(ean)) {
          await expect(image, `EAN ${ean}`).toHaveCount(0)
          continue
        }
        await expect(image, `EAN ${ean}`).toHaveAttribute('src', `${STORAGE}/public/product-images/barcodes/${ean}.png`)
        await expect
          .poll(() => image.evaluate((img) => /** @type {HTMLImageElement} */ (img).complete && /** @type {HTMLImageElement} */ (img).naturalWidth > 0), {
            message: `a imagem do EAN ${ean} não carregou`,
          })
          .toBe(true)
      }
      expect(signed, 'nunca se pede um URL assinado expirado').toEqual([])
    })
  }
})
