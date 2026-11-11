/**
 * Páginas do catálogo que o build não gerou (auditoria RP-04, FE-04, SEO-06).
 *
 * A loja é uma SPA, mas só existem como ficheiro as páginas que o pré-render escreveu no último deploy. Um modelo (ou
 * uma categoria) publicado depois dava HTTP 404 no link directo: partilhado por WhatsApp, recarregado, vindo do Google.
 * Aqui, quando o Pages não encontra o ficheiro de `/categoria/...` ou de `/produto/...`, vê-se na API se a página
 * existe e, se existir, serve-se a loja (`/`), que abre o modelo por cima. Se não existir, fica o 404 de verdade
 * (public/404.html, com HTTP 404), para os motores de busca não guardarem endereços inventados.
 *
 * A pergunta «existe?» usa as listas que a loja já lê (`/categorias`, e a lista de modelos da categoria) e que a cache
 * da Cloudflare já tem: um endereço inventado não custa um pedido à API. Se a API não responder, assume-se que existe
 * (a loja diz o que for): é melhor mostrar um erro do que um 404 num modelo que existe.
 */
import { categorySlug, isUuid, modelSlug, slugifyName } from '../../src/lib/catalogRoutes.js'
import { catalogJson } from './catalog-edge.js'

// Domínio canónico fixo: visitas por *.pages.dev não podem declarar-se canónicas (como em src/composables/usePageMeta.js).
const SITE_ORIGIN = 'https://www.diomika.com'

const CATEGORY_ROUTE = /^\/categoria\/([^/]+)(?:\/([^/]+))?\/?$/
const LEGACY_PRODUCT_ROUTE = /^\/produto\/([^/]+)\/?$/

const decode = (segment) => {
  try {
    return decodeURIComponent(segment)
  } catch {
    return null
  }
}

/**
 * A rota do catálogo de um caminho, ou null se não é uma.
 * @returns {{ category: string, model: string | null } | { legacyId: string } | null}
 */
export function catalogueRoute(pathname) {
  const legacy = LEGACY_PRODUCT_ROUTE.exec(pathname)
  if (legacy) {
    const legacyId = decode(legacy[1])
    return legacyId ? { legacyId } : null
  }
  const match = CATEGORY_ROUTE.exec(pathname)
  if (!match) return null
  const category = decode(match[1])
  const model = match[2] === undefined ? null : decode(match[2])
  return category && (match[2] === undefined || model) ? { category, model } : null
}

/**
 * A rota existe no catálogo? `true`, `false`, ou `null` se não se sabe (a API não respondeu).
 * @returns {Promise<boolean | null>}
 */
export async function catalogueRouteExists(context, route) {
  try {
    if ('legacyId' in route) {
      if (!isUuid(route.legacyId)) return false
      const { status } = await catalogJson(context, `/catalogo/modelo-detalhe/${route.legacyId}`)
      return status === 200 ? true : status === 404 ? false : null
    }

    const categories = await catalogJson(context, '/categorias')
    if (categories.status !== 200 || !Array.isArray(categories.data)) return null
    // O mesmo que a API aceita em /categorias/slug/: o endereço guardado ou o derivado do nome.
    const category = categories.data.find((entry) =>
      [categorySlug(entry), slugifyName(entry.nome), entry.slug].includes(route.category),
    )
    if (!category) return false
    if (!route.model) return true
    if (!category.tipo_catalogo) return null

    const models = await catalogJson(
      context,
      `/catalogo/${encodeURIComponent(category.tipo_catalogo)}/modelos-catalogo/${category.id}`,
    )
    if (models.status !== 200 || !Array.isArray(models.data)) return null
    return models.data.some((model) => [modelSlug(model), model.slug].includes(route.model))
  } catch {
    // A API em baixo, ou uma resposta que não se percebe: nunca deita abaixo a página.
    return null
  }
}

const escapeAttribute = (value) =>
  value.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;')

/**
 * A loja (`/`) para um endereço do catálogo que o build não gerou, ou `null` se não é caso disso: não é um GET, não é
 * uma rota do catálogo, ou a rota não existe. O `canonical` e o `og:url` do HTML passam a ser os do endereço pedido:
 * o `/` pré-renderizado traz os da página inicial, e um modelo novo declarava-se cópia dela.
 */
export async function catalogueFallback(context, url) {
  const { request, env } = context
  if (request.method !== 'GET' && request.method !== 'HEAD') return null
  const route = catalogueRoute(url.pathname)
  if (!route || (await catalogueRouteExists(context, route)) === false) return null

  // Um GET simples, sem os cabeçalhos do visitante: um `If-None-Match` dele daria 304 em vez da loja.
  const shell = await env.ASSETS.fetch(new Request(new URL('/', url)))
  if (shell.status !== 200) return null

  const canonical = escapeAttribute(`${SITE_ORIGIN}${url.pathname}`)
  const html = (await shell.text())
    .replace(/(<link rel="canonical" href=")[^"]*(")/, (_, open, close) => open + canonical + close)
    .replace(/(<meta property="og:url" content=")[^"]*(")/, (_, open, close) => open + canonical + close)

  const headers = new Headers(shell.headers)
  for (const name of ['content-length', 'content-encoding', 'etag']) headers.delete(name)
  headers.set('Cache-Control', 'public, max-age=0, must-revalidate')
  return new Response(html, { status: 200, headers })
}
