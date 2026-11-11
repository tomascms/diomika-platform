/**
 * Erros dos pedidos à API (FE-09): que estado mostrar e que mensagens por campo vieram.
 */

/**
 * Que estado mostrar quando uma página não consegue os seus dados.
 * `not-found`: o endereço já não existe (404, 410) ou o id nem é um id (400, 422): tentar de novo não resolve,
 * o visitante precisa de uma saída (a categoria, o catálogo). `unavailable`: rede, tempo esgotado, erro do
 * servidor ou um erro que não se conhece: tentar de novo pode resultar, e há WhatsApp e telefone.
 */
export const errorKind = (err) =>
  [400, 404, 410, 422].includes(err?.status) ? 'not-found' : 'unavailable'

/**
 * Corpo de um 422 da API → { campo: mensagem }, com o primeiro erro de cada campo. O nome do campo é o último
 * texto de `loc` (`["body", "nome"]` → `nome`); {} se o corpo não for uma lista de erros.
 */
export function fieldErrors(body) {
  const detail = body?.detail
  if (!Array.isArray(detail)) return {}
  const fields = {}
  for (const item of detail) {
    const name = [...(item?.loc ?? [])]
      .reverse()
      .find((part) => typeof part === 'string' && part !== 'body')
    if (name && item?.msg && !(name in fields)) fields[name] = String(item.msg)
  }
  return fields
}
