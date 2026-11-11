/**
 * Regras da quantidade de um artigo no pedido (auditoria: BR-03, FE-08, RP-12): múltiplo do passo da categoria,
 * com um mínimo e um máximo. A API e `isValidCartQty` (composables/useCart.js) aceitam exactamente isto.
 */

/** Quantidade máxima por artigo no pedido. */
export const MAX_QTY = 6000

/** Regras de quantidade de uma categoria ou de uma linha do pedido, alinhadas com a API (o mínimo nunca é menor do que o passo). */
export function resolveCartQtyRules(source = {}) {
  const step = Number(source.carrinho_step ?? source.carrinhoStep) || 6
  const minRaw = source.carrinho_min ?? source.carrinhoMin
  const min = minRaw != null && minRaw !== '' ? Number(minRaw) : step
  return { step, min: Math.max(min, step) }
}

/** A quantidade de uma linha cumpre as regras da sua categoria. */
export function isValidCartQty(qty, source = {}) {
  const { step, min } = resolveCartQtyRules(source)
  const q = Number(qty)
  return q >= min && q <= MAX_QTY && q % step === 0
}

/** Menor e maior quantidade válidas: ambas múltiplas do passo (o mínimo sobe ao múltiplo seguinte, o máximo desce). */
function limits(min, step, max) {
  const s = Number(step) > 0 ? Number(step) : 1
  const lowest = Math.ceil(Math.max(Number(min) || 0, s) / s) * s
  return { step: s, lowest, highest: Math.max(lowest, Math.floor(max / s) * s) }
}

/**
 * A quantidade válida que cobre o que se escreveu: o múltiplo do passo por excesso (100 com passo 12 passa a 108,
 * «o múltiplo seguinte» de RP-12), nunca abaixo do mínimo nem acima do máximo. O que não é número dá o mínimo.
 */
export function normalizeQuantity(value, min, step, max = MAX_QTY) {
  const { step: s, lowest, highest } = limits(min, step, max)
  const typed = Number(value)
  if (!Number.isFinite(typed)) return lowest
  return Math.min(highest, Math.max(lowest, Math.ceil(typed / s) * s))
}

/**
 * `normalizeQuantity` mais o aviso para o visitante quando a quantidade mudou («Quantidade ajustada de 100 para
 * 108 un.: vendemos em múltiplos de 12.»). Sem alteração, o aviso é ''.
 */
export function adjustQuantity(typed, min, step, max = MAX_QTY) {
  const value = normalizeQuantity(typed, min, step, max)
  const number = Number(typed)
  if (!Number.isFinite(number) || number === value) return { value, notice: '' }
  const { step: s, lowest, highest } = limits(min, step, max)
  let reason = `vendemos em múltiplos de ${s}.`
  if (number < lowest) reason = `o mínimo é ${lowest} un.`
  else if (number > highest) reason = `o máximo por pedido é ${highest} un.`
  return { value, notice: `Quantidade ajustada de ${number} para ${value} un.: ${reason}` }
}

/** «Vendido em caixas de 12 un.» quando o passo da categoria é a caixa (RP-08); senão ''. */
export function boxNote(box, step) {
  const units = Number(box)
  return Number.isInteger(units) && units > 0 && units === Number(step)
    ? `Vendido em caixas de ${units} un.`
    : ''
}
