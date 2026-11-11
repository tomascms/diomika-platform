/**
 * /sitemap.xml gerado a partir da API a cada pedido (auditoria SEO-06): um modelo publicado hoje entra no mapa hoje.
 * Antes só existia o que o pré-render escrevia no último deploy. As leituras vão pela cache da Cloudflare
 * (functions/_lib/catalog-edge.js), por isso um pedido custa umas leituras de cache e não um passeio pelos EUA.
 *
 * Se a API não responder, ou não houver nada para listar, serve o mapa que o build escreveu (dist/sitemap.xml): um
 * mapa de ontem é melhor do que um erro, e do que um mapa só com as páginas estáticas.
 *
 * ponytail: uma categoria custa ~3 subrequests com a cache fria e o plano grátis dá 50 por pedido: acima de ~12
 * categorias passa-se a um índice de mapas, um por categoria.
 */
import { STATIC_PAGES } from '../scripts/static-pages.mjs'
import { collectCatalogue } from '../src/lib/catalogue.js'
import { sitemapEntries, sitemapXml } from '../src/lib/sitemap.js'
import { catalogJson } from './_lib/catalog-edge.js'

// Domínio canónico fixo: o mapa lista sempre os endereços de www.diomika.com, venha o pedido de onde vier.
const SITE_ORIGIN = 'https://www.diomika.com'

export async function onRequest(context) {
  const { request, env } = context
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    return new Response('Método não suportado.', { status: 405, headers: { Allow: 'GET, HEAD' } })
  }
  try {
    const catalogue = await collectCatalogue(async (path) => {
      const { status, data } = await catalogJson(context, path)
      if (status !== 200) throw new Error(`HTTP ${status} ${path}`)
      return data
    })
    if (!catalogue.length) throw new Error('catálogo sem páginas')
    return new Response(sitemapXml(SITE_ORIGIN, sitemapEntries(STATIC_PAGES, catalogue)), {
      headers: {
        'Content-Type': 'application/xml; charset=utf-8',
        'Cache-Control': 'public, max-age=600',
      },
    })
  } catch {
    return env.ASSETS.fetch(request)
  }
}
