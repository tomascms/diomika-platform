/**
 * Páginas estáticas para SEO e pré-visualizações em redes sociais.
 *
 * A loja é uma SPA: sem isto, o Google via o mesmo <title> em todas as
 * páginas e o WhatsApp/Facebook (que não correm JavaScript) mostravam sempre
 * a pré-visualização genérica. Depois do `vite build`, este script pede o
 * catálogo público à API e escreve um HTML por categoria e por modelo, com
 * título, descrição, URL canónico, Open Graph, dados estruturados (JSON-LD) e
 * um bloco <noscript> com o conteúdo (para crawlers sem JavaScript). A app
 * Vue arranca por cima, igual.
 *
 * Ficheiros "x.html" (não "x/index.html"): o Cloudflare Pages serve
 * /categoria/almofada a partir de categoria/almofada.html sem redirecionar.
 *
 * Se a API não responder, ou o catálogo não der nenhuma página, o build FALHA (código 1): publicar assim retirava do
 * site as páginas de catálogo, sem aviso (SEO-06). O mapa do site vivo (functions/sitemap.xml.js) e as páginas do
 * catálogo que este script não gerou (functions/_middleware.js) vêm da mesma API, em cada pedido.
 *
 * Variáveis: VITE_API_BASE_URL (a API), SITE_ORIGIN, PRERENDER_DIST (a pasta com o `index.html` do `vite build`; por
 * omissão `dist`, os testes apontam-na para uma pasta temporária).
 */
import { mkdir, readdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { modelSlug } from '../src/lib/catalogRoutes.js'
import { collectCatalogue } from '../src/lib/catalogue.js'
import { categoryMeta, modelMeta, pretty } from '../src/lib/describe.js'
import { robotsTxt, sitemapEntries, sitemapXml } from '../src/lib/sitemap.js'
import { renderViews } from './render-views.mjs'
import { STATIC_PAGES } from './static-pages.mjs'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const DIST = process.env.PRERENDER_DIST ? path.resolve(process.env.PRERENDER_DIST) : path.join(ROOT, 'dist')
const SITE = (process.env.SITE_ORIGIN || 'https://www.diomika.com').replace(/\/+$/, '')
const API = (process.env.VITE_API_BASE_URL || 'https://api.diomika.com').replace(/\/+$/, '')
const DEFAULT_IMAGE = `${SITE}/icon-512.png`
const TIMEOUT_MS = 20000

const esc = (value) =>
  String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')

async function getJson(pathname) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  try {
    const resp = await fetch(`${API}${pathname}`, {
      headers: { Accept: 'application/json', 'User-Agent': 'DiomikaBuild/1.0 (prerender)' },
      signal: controller.signal,
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status} ${pathname}`)
    return await resp.json()
  } finally {
    clearTimeout(timer)
  }
}

/**
 * Primeira cor visível (a que a página de produto mostra primeiro), só se for URL pública
 * do Storage — então o srcset abaixo é igual ao do SoftImage e o preload é reaproveitado.
 */
const PUBLIC_IMAGE = /^https:\/\/[^/?]+\/storage\/v1\/object\/public\/[^?]+\.(png|jpe?g|webp)$/i

function heroImage(model) {
  const first = (model.modelo_cores || [])
    .filter((c) => c && c.visibilidade !== false)
    .sort((a, b) => a.numero - b.numero)[0]
  const url = String(first?.imagem || '')
  return PUBLIC_IMAGE.test(url) ? url : ''
}

/**
 * LCP: o `preload` da imagem que a página mostra primeiro, escrito no HTML para ela começar a descarregar sem esperar pelo
 * JS e pela API. Os candidatos são os do SoftImage (480 e 960, nunca o original, PERF-02) e o `sizes` é o dele.
 */
const preloadSrcset = (image, sizes) =>
  `<link rel="preload" as="image" fetchpriority="high" imagesrcset="${esc(`${image}.w480.webp 480w, ${image}.w960.webp 960w`)}" imagesizes="${esc(sizes)}">`
// Os cartões do catálogo pedem só a miniatura de 480 (SoftImage `thumb`, sem `sizes`).
const preloadThumb = (image) => `<link rel="preload" as="image" fetchpriority="high" href="${esc(`${image}.w480.webp`)}">`
const modulePreload = (href) => (href ? `<link rel="modulepreload" crossorigin href="${esc(href)}">` : '')

/** Primeira categoria com imagem pública do Storage, a que a página inicial e o catálogo mostram primeiro (PERF-07). */
function firstCategoryImage(catalogue) {
  for (const { category } of catalogue) {
    const url = String(category.imagem || '')
    if (PUBLIC_IMAGE.test(url)) return url
  }
  return ''
}

/** `assets/<Nome>-<hash>.js` do `vite build` (os chunks das vistas), para o `modulepreload`. */
async function viewChunks() {
  const files = await readdir(path.join(DIST, 'assets')).catch(() => [])
  return (name) => {
    const file = files.find((f) => f.startsWith(`${name}-`) && f.endsWith('.js'))
    return file ? `/assets/${file}` : ''
  }
}

function page(template, { urlPath, title, description, jsonLd = [], body = '', image = '', preload = [] }) {
  const fullTitle = title ? `${title} | Diomika` : 'Diomika — Têxteis para o lar'
  const url = `${SITE}${urlPath}`
  const head = [
    `<link rel="canonical" href="${esc(url)}">`,
    `<meta property="og:url" content="${esc(url)}">`,
    ...preload.filter(Boolean),
    ...jsonLd.map((d) => `<script type="application/ld+json">${JSON.stringify(d).replace(/</g, '\\u003c')}</script>`),
  ].join('\n    ')
  return template
    .replace(/<title>[^<]*<\/title>/, `<title>${esc(fullTitle)}</title>`)
    .replace(/(<meta name="description" content=")[^"]*(")/, `$1${esc(description)}$2`)
    .replace(/(<meta property="og:title" content=")[^"]*(")/, `$1${esc(fullTitle)}$2`)
    .replace(/(<meta property="og:description" content=")[^"]*(")/, `$1${esc(description)}$2`)
    .replace(/(<meta property="og:image" content=")[^"]*(")/, `$1${esc(image || DEFAULT_IMAGE)}$2`)
    .replace('</head>', () => `    ${head}\n  </head>`)
    .replace('<div id="app"></div>', () => `<div id="app"></div>\n    <noscript>${body}</noscript>`)
}

function breadcrumb(items) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((it, i) => ({ '@type': 'ListItem', position: i + 1, name: it.name, item: `${SITE}${it.path}` })),
  }
}

async function write(urlPath, html) {
  const file = urlPath === '/' ? path.join(DIST, 'index.html') : path.join(DIST, `${urlPath.replace(/^\/+/, '')}.html`)
  await mkdir(path.dirname(file), { recursive: true })
  await writeFile(file, html, 'utf8')
}

async function main() {
  const template = await readFile(path.join(DIST, 'index.html'), 'utf8')
  const chunk = await viewChunks()

  // O texto das páginas institucionais, as próprias vistas da loja, para o <noscript> (SEO-10): sem JavaScript viam-se só
  // o título e a descrição. Se uma não renderizar, o build falha, como com o catálogo.
  const views = await renderViews(STATIC_PAGES.filter((p) => p.noscript).map((p) => p.path))
  for (const p of STATIC_PAGES) {
    if (!p.title || p.path === '/') continue
    const body = views[p.path] ? `<main>${views[p.path]}</main>` : ''
    await write(p.path, page(template, { urlPath: p.path, title: p.title, description: p.description, body }))
  }

  // Sem catálogo não há loja: um build que o pedisse e não o tivesse publicava o site sem as páginas de catálogo.
  const catalogue = await collectCatalogue(getJson)
  if (!catalogue.length) throw new Error('o catálogo não tem nenhuma categoria com modelos para gerar')

  let pages = 0
  const catalogLinks = []
  for (const { category: cat, slug: cSlug, models } of catalogue) {
    const catName = pretty(cat.nome)
    const catPath = `/categoria/${cSlug}`
    const catDesc = categoryMeta(catName, models.length)
    const modelLinks = []

    for (const m of models) {
      const mSlug = modelSlug(m)
      const mPath = `${catPath}/${mSlug}`
      const cores = (m.modelo_cores || []).filter((c) => c && c.visibilidade !== false)
      const coresTxt = cores.map((c) => c.nome).filter(Boolean).slice(0, 8).join(', ')
      // Os mesmos título e descrição que a loja põe depois do JavaScript (src/lib/describe.js).
      const { title: mTitle, description: mDesc } = modelMeta(m, catName)
      const variants = Array.isArray(m.product_variants) ? m.product_variants : []
      const hero = heroImage(m)
      // Sem `offers`, de propósito (SEO-08): o catálogo não tem preços públicos e um preço inventado seria pior do que um
      // aviso no Search Console («sem fragmentos de produto»). É schema.org válido; com preços, acrescentar `offers`.
      const product = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        name: m.nome,
        description: mDesc,
        brand: { '@type': 'Brand', name: 'Diomika' },
        category: catName,
        url: `${SITE}${mPath}`,
        image: hero || DEFAULT_IMAGE,
        ...(variants[0]?.ean ? { gtin13: String(variants[0].ean) } : {}),
      }
      const body = `<main><nav><a href="/">Início</a> / <a href="${esc(catPath)}">${esc(catName)}</a></nav><h1>${esc(m.nome)}</h1><p>${esc(mDesc)}</p>${coresTxt ? `<p>Cores: ${esc(coresTxt)}</p>` : ''}<p><a href="/contacto">Pedir orçamento</a></p></main>`
      await write(mPath, page(template, {
        urlPath: mPath,
        title: mTitle,
        description: mDesc,
        jsonLd: [product, breadcrumb([{ name: 'Início', path: '/' }, { name: catName, path: catPath }, { name: m.nome, path: mPath }])],
        body,
        image: hero,
        preload: [hero && preloadSrcset(hero, '(max-width: 900px) 100vw, 50vw')],
      }))
      modelLinks.push(`<li><a href="${esc(mPath)}">${esc(m.nome)}</a></li>`)
      pages += 1
    }

    const itemList = {
      '@context': 'https://schema.org',
      '@type': 'ItemList',
      name: catName,
      itemListElement: models.map((m, i) => ({ '@type': 'ListItem', position: i + 1, url: `${SITE}${catPath}/${modelSlug(m)}`, name: m.nome })),
    }
    await write(catPath, page(template, {
      urlPath: catPath,
      title: catName,
      description: catDesc,
      jsonLd: [itemList, breadcrumb([{ name: 'Início', path: '/' }, { name: catName, path: catPath }])],
      body: `<main><h1>${esc(catName)}</h1><p>${esc(catDesc)}</p><ul>${modelLinks.join('')}</ul></main>`,
    }))
    catalogLinks.push(`<li><a href="${esc(catPath)}">${esc(catName)}</a></li>`)
    pages += 1
  }

  // Página inicial e catálogo também listam as categorias para crawlers sem JS.
  const lcp = firstCategoryImage(catalogue)
  const home = page(template, { urlPath: '/', title: '', preload: [lcp && preloadSrcset(lcp, '(max-width: 900px) 50vw, 25vw'), modulePreload(chunk('HomeView'))], description: 'Diomika: almofadas, assentos, toalhas de mesa, aventais e mais. Escolha modelos, cores e medidas e peça orçamento online.', body: `<main><h1>Têxteis para o lar, com proposta à medida.</h1><ul>${catalogLinks.join('')}</ul></main>` })
  await write('/', home)
  const cat = STATIC_PAGES.find((p) => p.path === '/categorias')
  await write('/categorias', page(template, { urlPath: '/categorias', title: cat.title, description: cat.description, preload: [lcp && preloadThumb(lcp), modulePreload(chunk('CategoriesView'))], body: `<main><h1>Catálogo</h1><ul>${catalogLinks.join('')}</ul></main>` }))

  // O mapa que o build escreve é o de reserva: functions/sitemap.xml.js gera o mesmo a partir da API a cada pedido.
  const entries = sitemapEntries(STATIC_PAGES, catalogue)
  await writeFile(path.join(DIST, 'sitemap.xml'), sitemapXml(SITE, entries), 'utf8')
  await writeFile(path.join(DIST, 'robots.txt'), robotsTxt(SITE, STATIC_PAGES), 'utf8')
  console.log(`[seo] ${pages} páginas de catálogo + ${STATIC_PAGES.length} estáticas; sitemap com ${entries.length} URLs`)
}

main().catch((err) => {
  console.error(`[seo] pré-renderização falhou: ${err.message}`)
  process.exitCode = 1
})
