/**
 * O recurso do catálogo (FE-13): pergunta-se à API e, se ela não responder (sem rede, tempo esgotado, erro 5xx), à base
 * de dados, só em leitura pública, como o resto do catálogo já faz (useCatalog.js). Um 404 ou um 422 é «não existe»:
 * a base de dados não ia dizer outra coisa, por isso esses não têm recurso. Se o recurso também falhar, o erro que
 * se mostra é o da API (é ele que diz ao ecrã de erro se foi rede ou servidor).
 *
 * @template T
 * @param {() => Promise<T>} fromApi
 * @param {() => Promise<T>} fromDatabase
 * @param {{ configured: boolean }} options `configured`: a loja sabe falar com a base de dados (Supabase)
 * @returns {Promise<T>}
 */
export async function withDatabaseFallback(fromApi, fromDatabase, { configured }) {
  try {
    return await fromApi()
  } catch (apiError) {
    const outage = Boolean(apiError?.network) || apiError?.status >= 500
    if (!configured || !outage) throw apiError
    try {
      return await fromDatabase()
    } catch {
      throw apiError
    }
  }
}
