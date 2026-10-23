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
 * Se a API não responder, o build continua — só fica sem estas páginas.
 */
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const DIST = path.join(ROOT, 'dist')
const SITE = (process.env.SITE_ORIGIN || 'https://www.diomika.com').replace(/\/+$/, '')
const API = (process.env.VITE_API_BASE_URL || 'https://api.diomika.com').replace(/\/+$/, '')
const DEFAULT_IMAGE = `${SITE}/icon-512.png`
const TIMEOUT_MS = 20000

const STATIC_PAGES = [
  { path: '/', changefreq: 'weekly', priority: '1.0' },
  { path: '/categorias', title: 'Catálogo', description: 'Todas as categorias do catálogo Diomika — almofadas, assentos, toalhas de mesa, aventais e mais.', changefreq: 'weekly', priority: '0.9' },
  { path: '/sobre', title: 'Sobre nós', description: 'Conheça a Diomika e como funciona o pedido de orçamento do catálogo B2B.', changefreq: 'monthly', priority: '0.6' },
  { path: '/contacto', title: 'Contacto', description: 'Fale com a equipa comercial da Diomika por telefone, WhatsApp ou mensagem.', changefreq: 'monthly', priority: '0.6' },
  { path: '/pesquisa', title: 'Pesquisa', description: 'Pesquise modelos no catálogo Diomika.', changefreq: 'weekly', priority: '0.5' },
  { path: '/privacidade', title: 'Política de Privacidade', description: 'Como a Diomika trata os dados pessoais recolhidos no site.', changefreq: 'yearly', priority: '0.2' },
  { path: '/termos', title: 'Termos e condições', description: 'Termos de utilização do site e do pedido de orçamento Diomika.', changefreq: 'yearly', priority: '0.2' },
  { path: '/cookies', title: 'Cookies', description: 'Que cookies o site Diomika usa e como gerir o consentimento.', changefreq: 'yearly', priority: '0.2' },
  // Sem página gerada, abrir o link directo (ou recarregar) mostrava o 404 estático.
  { path: '/carrinho', title: 'Pedido de orçamento', description: 'Reveja os produtos e envie o pedido de orçamento.', sitemap: false },
]

const esc = (value) =>
  String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')

const slugify = (value) =>
  String(value || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')

const isUuid = (v) => /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(v || ''))
// Mesmas regras que src/lib/catalogRoutes.js
const categorySlug = (c) => (c?.slug && !isUuid(c.slug) ? String(c.slug).trim() : slugify(c?.nome))
const modelSlug = (m) => slugify(m?.nome) || (m?.slug && !isUuid(m.slug) ? m.slug : '')
const pretty = (t) => {
  const s = String(t || '').trim()
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''
}
const realDescription = (d) => {
  const s = String(d || '').trim()
  return s && !/^sem descri/i.test(s) ? s : ''
}

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

/** Igual ao filtro da página de categoria: precisa de um EAN e de uma cor visível. */
function isShowable(model) {
  if (!model || model.visibilidade === false) return false
  const pt = model._storefront?.product_table || 'product_variants'
  const rows = Array.isArray(model[pt]) ? model[pt] : model[pt] ? [model[pt]] : []
  const hasEan = rows.some((p) => String(p?.ean || '').trim())
  const hasColor = (model.modelo_cores || []).some((c) => c && c.visibilidade !== false)
  return hasEan && hasColor
}

/**
 * Primeira cor visível (a que a página de produto mostra primeiro), só se for URL pública
 * do Storage — então o srcset abaixo é igual ao do SoftImage e o preload é reaproveitado.
 */
function heroImage(model) {
  const first = (model.modelo_cores || [])
    .filter((c) => c && c.visibilidade !== false)
    .sort((a, b) => a.numero - b.numero)[0]
  const url = String(first?.imagem || '')
  return /^https:\/\/[^/?]+\/storage\/v1\/object\/public\/[^?]+\.(png|jpe?g|webp)$/i.test(url) ? url : ''
}

function page(template, { urlPath, title, description, jsonLd = [], body = '', image = '' }) {
  const fullTitle = title ? `${title} | Diomika` : 'Diomika — Têxteis para o lar, para revenda'
  const url = `${SITE}${urlPath}`
  const head = [
    `<link rel="canonical" href="${esc(url)}">`,
    `<meta property="og:url" content="${esc(url)}">`,
    // LCP: a imagem começa a descarregar com o HTML, sem esperar pelo JS e pela API.
    ...(image
      ? [`<link rel="preload" as="image" fetchpriority="high" imagesrcset="${esc(`${image}.w480.webp 480w, ${image}.w960.webp 960w, ${image} 1600w`)}" imagesizes="(max-width: 900px) 100vw, 50vw">`]
      : []),
    ...jsonLd.map((d) => `<script type="application/ld+json">${JSON.stringify(d).replace(/</g, '\\u003c')}</script>`),
  ].join('\n    ')
  return template
    .replace(/<title>[^<]*<\/title>/, `<title>${esc(fullTitle)}</title>`)
    .replace(/(<meta name="description" content=")[^"]*(")/, `$1${esc(description)}$2`)
    .replace(/(<meta property="og:title" content=")[^"]*(")/, `$1${esc(fullTitle)}$2`)
    .replace(/(<meta property="og:description" content=")[^"]*(")/, `$1${esc(description)}$2`)
    .replace(/(<meta property="og:image" content=")[^"]*(")/, `$1${esc(image || DEFAULT_IMAGE)}$2`)
    .replace('</head>', `    ${head}\n  </head>`)
    .replace('<div id="app"></div>', `<div id="app"></div>\n    <noscript>${body}</noscript>`)
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

function sitemap(entries) {
  const today = new Date().toISOString().slice(0, 10)
  const urls = entries
    .map((e) => `  <url><loc>${esc(SITE + e.path)}</loc><lastmod>${(e.lastmod || today).slice(0, 10)}</lastmod><changefreq>${e.changefreq}</changefreq><priority>${e.priority}</priority></url>`)
    .join('\n')
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`
}

async function main() {
  const template = await readFile(path.join(DIST, 'index.html'), 'utf8')
  const entries = STATIC_PAGES.filter((p) => p.sitemap !== false)

  for (const p of STATIC_PAGES) {
    if (!p.title || p.path === '/') continue
    await write(p.path, page(template, { urlPath: p.path, title: p.title, description: p.description }))
  }

  let categories = []
  try {
    categories = (await getJson('/categorias')).filter((c) => c && c.visibilidade !== false)
  } catch (err) {
    console.warn(`[seo] API indisponível — só páginas estáticas (${err.message})`)
  }

  let pages = 0
  const catalogLinks = []
  for (const cat of categories) {
    const cSlug = categorySlug(cat)
    if (!cSlug || !cat.tipo_catalogo) continue
    let models = []
    try {
      const data = await getJson(`/catalogo/${encodeURIComponent(cat.tipo_catalogo)}/modelos-catalogo/${cat.id}`)
      models = (Array.isArray(data) ? data : data?.items || []).filter(isShowable)
    } catch (err) {
      console.warn(`[seo] ${cat.nome}: ${err.message}`)
      continue
    }
    if (!models.length) continue // categoria vazia: não se anuncia a motores de busca

    const catName = pretty(cat.nome)
    const catPath = `/categoria/${cSlug}`
    const catDesc = `${catName} para revenda: ${models.length} ${models.length === 1 ? 'modelo' : 'modelos'} em várias cores e medidas. Peça orçamento à Diomika — pedido mínimo 500 € + IVA.`
    const modelLinks = []

    for (const m of models) {
      const mSlug = modelSlug(m)
      if (!mSlug) continue
      const mPath = `${catPath}/${mSlug}`
      const desc = realDescription(m.descricao)
      const cores = (m.modelo_cores || []).filter((c) => c && c.visibilidade !== false)
      const coresTxt = cores.map((c) => c.nome).filter(Boolean).slice(0, 8).join(', ')
      const mDesc = (desc || `${m.nome} — ${catName.toLowerCase()} disponível em ${cores.length} ${cores.length === 1 ? 'cor' : 'cores'}${coresTxt ? ` (${coresTxt})` : ''}.`) + ' Peça orçamento à Diomika.'
      const variants = Array.isArray(m.product_variants) ? m.product_variants : []
      const hero = heroImage(m)
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
        title: `${m.nome} — ${catName}`,
        description: mDesc,
        jsonLd: [product, breadcrumb([{ name: 'Início', path: '/' }, { name: catName, path: catPath }, { name: m.nome, path: mPath }])],
        body,
        image: hero,
      }))
      entries.push({ path: mPath, changefreq: 'weekly', priority: '0.7', lastmod: m.updated_at })
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
    entries.push({ path: catPath, changefreq: 'weekly', priority: '0.8' })
    catalogLinks.push(`<li><a href="${esc(catPath)}">${esc(catName)}</a></li>`)
    pages += 1
  }

  if (catalogLinks.length) {
    // Página inicial e catálogo também listam as categorias para crawlers sem JS.
    const home = page(template, { urlPath: '/', title: '', description: 'Catálogo B2B da Diomika: almofadas, assentos, toalhas de mesa, aventais e mais. Escolha modelos, cores e medidas e peça orçamento online.', body: `<main><h1>Têxteis para o lar, prontos para a sua loja.</h1><ul>${catalogLinks.join('')}</ul></main>` })
    await write('/', home)
    const cat = STATIC_PAGES.find((p) => p.path === '/categorias')
    await write('/categorias', page(template, { urlPath: '/categorias', title: cat.title, description: cat.description, body: `<main><h1>Catálogo</h1><ul>${catalogLinks.join('')}</ul></main>` }))
  }

  await writeFile(path.join(DIST, 'sitemap.xml'), sitemap(entries), 'utf8')
  await writeFile(path.join(DIST, 'robots.txt'), `User-agent: *\nAllow: /\nDisallow: /carrinho\nDisallow: /api/\n\nSitemap: ${SITE}/sitemap.xml\n`, 'utf8')
  console.log(`[seo] ${pages} páginas de catálogo + ${STATIC_PAGES.length} estáticas; sitemap com ${entries.length} URLs`)
}

main().catch((err) => {
  console.warn(`[seo] pré-renderização ignorada: ${err.message}`)
})
