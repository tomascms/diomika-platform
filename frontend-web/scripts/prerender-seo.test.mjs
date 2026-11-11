import { test } from 'node:test'
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { withFixtureApi as withApi } from '../e2e/local/fixtureApi.js'

// Corre o pré-render a sério (como `npm run build`), numa pasta temporária e contra uma API de mentira em localhost
// que responde com as fixtures do e2e (e2e/local/fixtureApi.js): nunca toca no `dist` nem na produção.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

/** O pré-render sobre uma pasta nova com o `index.html` da loja. */
async function prerender(api, { chunks = [] } = {}) {
  const dist = mkdtempSync(path.join(tmpdir(), 'diomika-prerender-'))
  copyFileSync(path.join(ROOT, 'index.html'), path.join(dist, 'index.html'))
  // Os chunks das vistas que o `vite build` deixa em assets/ (o `modulepreload` procura-os pelo nome).
  if (chunks.length) mkdirSync(path.join(dist, 'assets'))
  for (const name of chunks) writeFileSync(path.join(dist, 'assets', name), '')
  const child = spawn(process.execPath, [path.join(ROOT, 'scripts', 'prerender-seo.mjs')], {
    env: { ...process.env, VITE_API_BASE_URL: api, PRERENDER_DIST: dist, SITE_ORIGIN: 'https://www.diomika.com' },
  })
  let output = ''
  child.stdout.on('data', (chunk) => (output += chunk))
  child.stderr.on('data', (chunk) => (output += chunk))
  const code = await new Promise((resolve) => child.on('close', resolve))
  const read = (file) => readFileSync(path.join(dist, file), 'utf8')
  const has = (file) => existsSync(path.join(dist, file))
  return { code, output, read, has, dist, clean: () => rmSync(dist, { recursive: true, force: true }) }
}

const htmlFiles = (dist) =>
  readdirSync(dist, { recursive: true, encoding: 'utf8' })
    .map((file) => file.split(path.sep).join('/'))
    .filter((file) => file.startsWith('categoria/') && file.endsWith('.html'))

test('com a API a responder escreve a página de cada categoria com modelos e de cada modelo, e o mapa do site', async () => {
  await withApi({}, async (api) => {
    const result = await prerender(api)
    try {
      assert.equal(result.code, 0, result.output)
      const pages = htmlFiles(result.dist)
      // 6 categorias com modelos e 26 modelos; Guarda-Chuva, Passadeira e Regional não têm nada e não têm página.
      assert.equal(pages.filter((file) => file.split('/').length === 2).length, 6)
      assert.equal(pages.filter((file) => file.split('/').length === 3).length, 26)
      assert.ok(result.has('categoria/almofada.html') && result.has('categoria/almofada/agate.html'))
      assert.ok(!result.has('categoria/guarda-chuvas.html') && !result.has('categoria/regional.html'))
      // As páginas estáticas, a página inicial com as categorias, o mapa e o robots.
      for (const file of ['sobre.html', 'contacto.html', 'carrinho.html', 'categorias.html', 'robots.txt', 'sitemap.xml']) {
        assert.ok(result.has(file), file)
      }
      assert.match(result.read('index.html'), /<noscript><main><h1>Têxteis para o lar[^]*<a href="\/categoria\/almofada">Almofada<\/a>/)
      assert.ok(!/guarda-chuvas/.test(result.read('index.html')))
      assert.ok(result.read('categoria/almofada/agate.html').includes('<link rel="canonical" href="https://www.diomika.com/categoria/almofada/agate">'))

      const sitemap = result.read('sitemap.xml')
      const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((match) => match[1])
      assert.ok(urls.includes('https://www.diomika.com/categoria/almofada/agate'))
      assert.equal(urls.filter((url) => url.includes('/categoria/')).length, 32)
      assert.ok(!/guarda-chuvas|regional|passadeiras/.test(sitemap))
      // Só com data real: as páginas estáticas não levam `lastmod`.
      assert.match(sitemap, /<loc>https:\/\/www\.diomika\.com\/sobre<\/loc><changefreq>/)

      // As páginas institucionais levam o texto da vista no <noscript>, com um <h1> (SEO-10); as que não se anunciam, não.
      for (const [file, phrase] of [
        ['sobre.html', 'Têxteis para o lar, de Caldas das Taipas'],
        ['privacidade.html', 'DIOMIKA INTERNACIONAL, UNIPESSOAL, LDA'],
        ['termos.html', 'Livro de Reclamações'],
        ['cookies.html', 'Cloudflare Turnstile'],
        ['condicoes-de-venda.html', 'Condições gerais de venda'],
        ['perguntas-frequentes.html', 'Perguntas frequentes'],
        ['contacto.html', 'Nome'],
        ['pesquisa.html', 'Pesquisar catálogo'],
      ]) {
        const html = result.read(file)
        const noscript = /<noscript>([\s\S]*?)<\/noscript>/.exec(html)?.[1] ?? ''
        assert.match(noscript, /^<main>[\s\S]*<h1[\s>]/, `${file}: <noscript> sem <h1>`)
        assert.ok(noscript.includes(phrase), `${file}: <noscript> sem «${phrase}»`)
      }
      assert.match(result.read('carrinho.html'), /<noscript><\/noscript>/)
    } finally {
      result.clean()
    }
  })
})

test('API em baixo: o build falha em vez de publicar o site sem as páginas de catálogo', async () => {
  // Uma porta onde não há nada: a ligação é recusada.
  const closed = await withApi({}, async (api) => api)
  const result = await prerender(closed)
  try {
    assert.equal(result.code, 1)
    assert.match(result.output, /pré-renderização falhou/)
    assert.ok(htmlFiles(result.dist).length === 0)
  } finally {
    result.clean()
  }
})

test('a API responde mas o catálogo vem vazio, ou uma categoria falha: o build falha', async () => {
  await withApi({ '/categorias': () => [200, []] }, async (api) => {
    const result = await prerender(api)
    try {
      assert.equal(result.code, 1)
      assert.match(result.output, /nenhuma categoria com modelos/)
    } finally {
      result.clean()
    }
  })

  const almofadas = '/catalogo/almofada/modelos-catalogo/4bba6298-b2d8-4d80-9303-49118f2bb29c'
  await withApi({ [almofadas]: () => [503, { detail: 'indisponível' }] }, async (api) => {
    const result = await prerender(api)
    try {
      assert.equal(result.code, 1)
      assert.match(result.output, /HTTP 503/)
    } finally {
      result.clean()
    }
  })
})

test('um 404.html com o seu CSS vai no build (o Pages serve-o, com HTTP 404, a qualquer endereço que não existe)', () => {
  const publicDir = path.join(ROOT, 'public')
  const html = readFileSync(path.join(publicDir, '404.html'), 'utf8')
  assert.match(html, /<link rel="stylesheet" href="\/404\.css">/)
  assert.ok(existsSync(path.join(publicDir, '404.css')))
})

test('PERF-07 e PERF-02: o início e o catálogo pré-carregam a 1.ª imagem e o chunk da vista; nenhum preload pede o original', async () => {
  await withApi({}, async (api) => {
    const result = await prerender(api, { chunks: ['HomeView-abc123.js', 'CategoriesView-def456.js', 'HomeView-abc123.css'] })
    try {
      assert.equal(result.code, 0, result.output)
      // A 1.ª categoria com imagem pública é a da fixture (a mesma que a página inicial mostra primeiro).
      const first = 'https://your-project-ref.supabase.co/storage/v1/object/public/product-images/categories/imagem/e9d1f8c70d484f2480c3f4e55c2e9677.webp'
      const home = result.read('index.html')
      assert.ok(home.includes(`imagesrcset="${first}.w480.webp 480w, ${first}.w960.webp 960w"`), 'início sem preload da imagem')
      assert.ok(home.includes('imagesizes="(max-width: 900px) 50vw, 25vw"'))
      assert.ok(home.includes('<link rel="modulepreload" crossorigin href="/assets/HomeView-abc123.js">'))
      assert.ok(!home.includes('CategoriesView-'), 'o início não pré-carrega a vista do catálogo')

      const categories = result.read('categorias.html')
      assert.ok(categories.includes(`<link rel="preload" as="image" fetchpriority="high" href="${first}.w480.webp">`))
      assert.ok(categories.includes('<link rel="modulepreload" crossorigin href="/assets/CategoriesView-def456.js">'))

      // Os modelos: o srcset do preload é o do SoftImage, 480 e 960, sem o original a 1600w.
      for (const file of htmlFiles(result.dist).filter((f) => f.split('/').length === 3)) {
        const html = result.read(file)
        for (const [, srcset] of html.matchAll(/imagesrcset="([^"]*)"/g)) {
          assert.ok(!/ 1600w/.test(srcset), `${file}: preload com o original`)
          assert.match(srcset, /\.w480\.webp 480w, .*\.w960\.webp 960w$/)
        }
      }
      assert.ok(result.read('categoria/almofada/foglia.html').includes('imagesrcset='), 'a Foglia perdeu o preload')
    } finally {
      result.clean()
    }
  })
})

test('sem os chunks em assets/ (o teste não corre o vite build) a página escreve-se na mesma, sem modulepreload', async () => {
  await withApi({}, async (api) => {
    const result = await prerender(api)
    try {
      assert.equal(result.code, 0, result.output)
      assert.ok(!result.read('index.html').includes('modulepreload'))
    } finally {
      result.clean()
    }
  })
})
