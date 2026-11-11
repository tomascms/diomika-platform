/**
 * O catálogo público tal como a loja o mostra, lido da API: as categorias com modelos mostráveis e esses modelos
 * (auditoria SEO-06, RP-04). Serve o pré-render (scripts/prerender-seo.mjs, no build) e o mapa do site vivo
 * (functions/sitemap.xml.js, na Cloudflare): as duas saídas listam as mesmas páginas porque saem desta função.
 * JavaScript simples, sem o alias «@» nem APIs do browser, como lib/describe.js.
 */
import { categorySlug, modelSlug } from './catalogRoutes.js'
import { showableModel } from './storefrontFormat.js'

/**
 * @param {(path: string) => Promise<any>} getJson lê um caminho da API (`/categorias`, …); tem de lançar se falhar
 * @returns {Promise<{ category: object, slug: string, models: object[] }[]>} só as categorias com pelo menos um modelo
 *   mostrável; cada modelo tem endereço (`modelSlug`)
 */
export async function collectCatalogue(getJson) {
  const raw = await getJson('/categorias')
  const categories = (Array.isArray(raw) ? raw : []).filter(
    (category) =>
      category &&
      category.visibilidade !== false &&
      category.tipo_catalogo &&
      categorySlug(category),
  )
  const sections = await Promise.all(
    categories.map(async (category) => {
      const data = await getJson(
        `/catalogo/${encodeURIComponent(category.tipo_catalogo)}/modelos-catalogo/${category.id}`,
      )
      const models = (Array.isArray(data) ? data : data?.items || []).filter(
        (model) => showableModel(model) && modelSlug(model),
      )
      return { category, slug: categorySlug(category), models }
    }),
  )
  // Uma categoria vazia não se anuncia aos motores de busca (e a loja já não a lista).
  return sections.filter((section) => section.models.length)
}
