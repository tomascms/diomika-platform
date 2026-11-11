// @ts-check
// Páginas com conteúdo sem JavaScript (auditoria: SEO-10): o que um motor de busca, um assistente de IA ou a pré-visualização
// do WhatsApp veem, que não correm JavaScript. Faz o que o deploy faz: corre o pré-render (scripts/prerender-seo.mjs) sobre a
// loja construída, contra a API de mentira (fixtures), e abre o resultado num browser SEM JavaScript.
import { spawn } from 'node:child_process'
import { cpSync, createReadStream, existsSync, mkdtempSync, rmSync, statSync } from 'node:fs'
import { createServer } from 'node:http'
import { tmpdir } from 'node:os'
import path from 'node:path'
import process from 'node:process'
import { test, expect } from '@playwright/test'
import { withFixtureApi } from './fixtureApi.js'

// A loja construída pelo servidor de teste (playwright.config.js: OUT_DIR); a pasta é sempre nova.
const BUILD = path.resolve('node_modules/.cache/e2e-dist')

/** @type {string} */
let dist
/** @type {import('node:http').Server} */
let server
/** @type {string} */
let origin

/** Os ficheiros de `dist` como o Pages os serve: /sobre é sobre.html, o que não existe dá o 404.html com HTTP 404. */
function serve(root) {
  return createServer((request, response) => {
    const { pathname } = new URL(request.url ?? '/', 'http://localhost')
    const candidates = [pathname === '/' ? 'index.html' : pathname.slice(1), `${pathname.slice(1)}.html`]
    const file = candidates.map((name) => path.join(root, name)).find((f) => existsSync(f) && statSync(f).isFile())
    const found = file ?? path.join(root, '404.html')
    const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript' }
    response.writeHead(file ? 200 : 404, { 'Content-Type': types[path.extname(found)] ?? 'application/octet-stream' })
    createReadStream(found).pipe(response)
  })
}

test.beforeAll(async () => {
  test.setTimeout(120_000)
  dist = mkdtempSync(path.join(tmpdir(), 'diomika-e2e-prerender-'))
  cpSync(BUILD, dist, { recursive: true })
  await withFixtureApi({}, async (api) => {
    const child = spawn(process.execPath, ['scripts/prerender-seo.mjs'], {
      env: { ...process.env, VITE_API_BASE_URL: api, PRERENDER_DIST: dist, SITE_ORIGIN: 'https://www.diomika.com' },
    })
    let output = ''
    child.stdout.on('data', (chunk) => (output += chunk))
    child.stderr.on('data', (chunk) => (output += chunk))
    const code = await new Promise((resolve) => child.on('close', resolve))
    expect(code, output).toBe(0)
  })
  server = serve(dist)
  await new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(undefined)))
  const address = /** @type {import('node:net').AddressInfo} */ (server.address())
  origin = `http://127.0.0.1:${address.port}`
})

test.afterAll(async () => {
  await new Promise((resolve) => server?.close(resolve))
  if (dist) rmSync(dist, { recursive: true, force: true })
})

// Sem JavaScript: o que está no HTML é tudo o que há.
test.use({ javaScriptEnabled: false })

const INSTITUTIONAL = [
  ['/sobre', 'Têxteis para o lar, de Caldas das Taipas', 'Vendemos a lojas, hotelaria e particulares'],
  ['/contacto', 'Contacto', '935 745 663'],
  ['/pesquisa', 'Pesquisar catálogo', 'Pesquise por categoria'],
  ['/privacidade', 'Política de Privacidade', 'DIOMIKA INTERNACIONAL, UNIPESSOAL, LDA'],
  ['/termos', 'Informação legal', 'Livro de Reclamações'],
  ['/cookies', 'Política de Cookies', 'Cloudflare Turnstile'],
  ['/condicoes-de-venda', 'Condições Gerais de Venda', 'proposta'],
  ['/perguntas-frequentes', 'Perguntas frequentes', 'Vendem a particulares?'],
]

test.describe('páginas institucionais', () => {
  for (const [route, heading, text] of INSTITUTIONAL) {
    test(`${route}: tem um título <h1> e o texto da página, sem JavaScript`, async ({ page }) => {
      await page.goto(`${origin}${route}`)

      await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
      await expect(page.getByRole('heading', { level: 1 })).toHaveText(heading)
      await expect(page.locator('main')).toContainText(text)
      // O título da página e o canonical são os da própria página, não os da página inicial.
      await expect(page).toHaveTitle(new RegExp(` \\| Diomika$`))
      await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', `https://www.diomika.com${route}`)
    })
  }
})

test.describe('o resto do site', () => {
  test('o início e o catálogo listam as categorias, e uma categoria os seus modelos', async ({ page }) => {
    await page.goto(`${origin}/`)
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Têxteis para o lar')
    await expect(page.getByRole('link', { name: 'Almofada', exact: true })).toBeVisible()
    await expect(page.locator('main')).not.toContainText('Guarda-Chuva') // vazia: não se anuncia

    await page.goto(`${origin}/categoria/almofada`)
    await expect(page.getByRole('heading', { level: 1, name: 'Almofada' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Agate' })).toBeVisible()
  })

  test('o 404 de uma categoria que não existe é a página 404 estática, com HTTP 404', async ({ page }) => {
    const response = await page.goto(`${origin}/categoria/nao-existe`)

    expect(response?.status()).toBe(404)
    await expect(page.getByRole('heading', { level: 1, name: 'Página não encontrada' })).toBeVisible()
  })

  test('o mapa e o robots.txt do build', async ({ request }) => {
    const sitemap = await (await request.get(`${origin}/sitemap.xml`)).text()
    expect(sitemap).toContain('<loc>https://www.diomika.com/categoria/almofada/agate</loc>')
    expect(sitemap).not.toContain('<lastmod></lastmod>')
    const robots = await (await request.get(`${origin}/robots.txt`)).text()
    expect(robots).toContain('Sitemap: https://www.diomika.com/sitemap.xml')
    expect(robots).not.toMatch(/\*\.xml/)
  })
})
