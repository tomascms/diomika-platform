/**
 * Proxy `/api` da loja: leituras públicas do catálogo, servidas da cache da Cloudflare (ver
 * functions/_lib/catalog-edge.js). Só GET de rotas públicas de catálogo. Formulários (POST) continuam a ir
 * directamente a api.diomika.com.
 */
import { UpstreamError, cacheableRoute, catalogFetch, forBrowser, json, normalizedSearch } from '../_lib/catalog-edge.js'

export async function onRequest(context) {
  const { request } = context
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    return json(405, { detail: 'Método não suportado.' }, { Allow: 'GET, HEAD' })
  }

  const url = new URL(request.url)
  const path = url.pathname.replace(/^\/api/, '') || '/'
  const route = cacheableRoute(path)
  if (!route) {
    return json(404, { detail: 'Não encontrado.' })
  }

  try {
    // Só a query que a rota conhece (SEG-12): a chave e o pedido à API levam o mesmo.
    const { body, status, contentType, cache } = await catalogFetch(context, path, normalizedSearch(route, url.searchParams))
    return forBrowser(body, status, contentType, cache)
  } catch (error) {
    if (!(error instanceof UpstreamError)) throw error
    return json(502, { detail: 'Sem ligação ao servidor. Tente de novo dentro de instantes.' })
  }
}
