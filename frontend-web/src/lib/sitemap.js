/**
 * Mapa do site (sitemap.xml) das páginas públicas da loja: as estáticas (scripts/static-pages.mjs) e, do catálogo,
 * as categorias com modelos e esses modelos (lib/catalogue.js). Serve o pré-render, que o escreve no build, e
 * functions/sitemap.xml.js, que o gera a partir da API em cada pedido: um modelo publicado hoje entra no mapa hoje, sem
 * esperar por um deploy (auditoria SEO-06). JavaScript simples, sem o alias «@» nem APIs do browser.
 */
import { modelSlug } from './catalogRoutes.js'

const xmlEscape = (value) =>
  String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')

/** `2026-10-03` de uma data ISO («2026-10-03T16:06:27+00:00»); '' se não for uma data (não se inventa uma). */
const day = (iso) => (/^\d{4}-\d{2}-\d{2}/.test(String(iso ?? '')) ? String(iso).slice(0, 10) : '')

/**
 * As entradas do mapa. `lastmod` só com data real (SEO-11): a das páginas estáticas era a do dia do build e dizia aos
 * motores de busca que tudo mudava em cada deploy; a de uma categoria é a do modelo mais recente.
 * @param {{ path: string, changefreq?: string, priority?: string, sitemap?: boolean }[]} staticPages
 * @param {{ slug: string, models: object[] }[]} catalogue o resultado de `collectCatalogue`
 * @returns {{ path: string, changefreq: string, priority: string, lastmod: string }[]}
 */
export function sitemapEntries(staticPages, catalogue) {
  const entries = staticPages
    .filter((page) => page.sitemap !== false)
    .map(({ path, changefreq, priority }) => ({ path, changefreq, priority, lastmod: '' }))
  for (const { slug, models } of catalogue) {
    const base = `/categoria/${slug}`
    const newest =
      models
        .map((model) => day(model.updated_at))
        .filter(Boolean)
        .sort()
        .at(-1) ?? ''
    entries.push({ path: base, changefreq: 'weekly', priority: '0.8', lastmod: newest })
    for (const model of models) {
      entries.push({
        path: `${base}/${modelSlug(model)}`,
        changefreq: 'weekly',
        priority: '0.7',
        lastmod: day(model.updated_at),
      })
    }
  }
  return entries
}

/**
 * O robots.txt: tudo permitido menos o que tem página gerada mas não se anuncia (`sitemap: false` em static-pages.mjs: o
 * pedido, o pedido rápido, o catálogo para imprimir) e a API; e onde está o mapa. O pré-render escreve-o e
 * public/robots.txt, o de reserva, tem de ser igual (um teste confere): o antigo bloqueava `*.xml`, isto é, o próprio
 * mapa, e apontava para ele com um endereço relativo (SEO-11).
 * @param {string} site a origem, sem barra final
 * @param {{ path: string, sitemap?: boolean }[]} staticPages
 */
export function robotsTxt(site, staticPages) {
  const hidden = staticPages
    .filter((page) => page.sitemap === false)
    .map((page) => `Disallow: ${page.path}`)
  return `User-agent: *\nAllow: /\n${[...hidden, 'Disallow: /api/'].join('\n')}\n\nSitemap: ${site}/sitemap.xml\n`
}

/** @param {string} site a origem, sem barra final (https://www.diomika.com) */
export function sitemapXml(site, entries) {
  const urls = entries
    .map(
      (entry) =>
        `  <url><loc>${xmlEscape(site + entry.path)}</loc>${entry.lastmod ? `<lastmod>${entry.lastmod}</lastmod>` : ''}<changefreq>${entry.changefreq}</changefreq><priority>${entry.priority}</priority></url>`,
    )
    .join('\n')
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`
}
