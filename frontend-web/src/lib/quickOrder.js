/**
 * Pedido rápido por EAN (auditoria RP-14): quem já conhece as referências cola uma linha por artigo,
 * «EAN; cor; quantidade», e junta tudo ao pedido de uma vez, em vez de abrir produto a produto.
 */
import { cartItemFor } from './cartItem.js'
import { adjustQuantity, resolveCartQtyRules } from './quantity.js'

/** Linhas que a API aceita num pedido (backend-api/core/rate_limit.py, MAX_PUBLIC_BODY_LINES). */
export const MAX_QUOTE_LINES = 50

const FORMAT_HELP = 'Escreva «EAN; cor; quantidade» (a cor pode faltar nos artigos de uma só cor).'

/**
 * Lê o texto colado. Uma linha por artigo; os campos separam-se por «;», vírgula, tabulação (colar de uma folha de
 * cálculo) ou espaços. Linhas em branco não contam. Um EAN repetido na mesma cor só vale na primeira linha.
 * @returns {{ rows: { n: number, raw: string, ean: string, color: number|null, quantity: number }[],
 *             errors: { n: number, raw: string, message: string }[] }}
 */
export function parseQuickOrder(text) {
  const rows = []
  const errors = []
  const seen = new Map()
  String(text ?? '')
    .split(/\r?\n/)
    .forEach((rawLine, index) => {
      const raw = rawLine.trim()
      if (!raw) return
      const n = index + 1
      const fail = (message) => errors.push({ n, raw, message })
      const fields = (/[;,\t]/.test(raw) ? raw.split(/[;,\t]/) : raw.split(/\s+/))
        .map((f) => f.trim())
        .filter(Boolean)
      if (fields.length < 2 || fields.length > 3) return fail(FORMAT_HELP)
      const [ean, ...rest] = fields
      const quantityText = rest[rest.length - 1]
      const colorText = rest.length === 2 ? rest[0] : null
      if (!/^\d{13}$/.test(ean)) return fail('O EAN tem 13 dígitos.')
      if (colorText !== null && !/^[1-9]\d*$/.test(colorText))
        return fail('A cor é o número da cor (por exemplo, 12).')
      if (!/^[1-9]\d*$/.test(quantityText))
        return fail('A quantidade é um número inteiro (por exemplo, 240).')
      const key = `${ean}|${colorText ?? ''}`
      if (seen.has(key)) return fail(`Repetido: este artigo já está na linha ${seen.get(key)}.`)
      seen.set(key, n)
      rows.push({
        n,
        raw,
        ean,
        color: colorText === null ? null : Number(colorText),
        quantity: Number(quantityText),
      })
    })
  return { rows, errors }
}

/** O modelo que tem este EAN entre os resultados da pesquisa, e a linha de produto certa (a pesquisa também apanha EAN parecidos). */
export function findByEan(ean, hits) {
  for (const hit of Array.isArray(hits) ? hits : []) {
    const model = hit?.model
    const table = model?._storefront?.product_table
    const rows = table ? [].concat(model[table] ?? []) : []
    const product = rows.find((row) => String(row?.ean ?? '').trim() === ean)
    if (product) return { model, category: model.categories ?? hit.category ?? {}, product }
  }
  return null
}

const visibleColors = (model) =>
  (model.modelo_cores || [])
    .filter((c) => c && c.visibilidade !== false)
    .sort((a, b) => a.numero - b.numero)

/**
 * Uma linha lida + o que a loja sabe do EAN → a linha do pedido, ou o motivo de não poder ser.
 * A quantidade segue as regras da categoria: um múltiplo inválido sobe ao seguinte, com aviso (como na ficha).
 * `color` vai junto para a loja pôr a imagem da cor na miniatura do pedido.
 * @returns {{ ok: true, item: object, color: object, notice: string, label: string } | { ok: false, message: string }}
 */
export function resolveQuickLine(row, found) {
  if (!found) return { ok: false, message: `O EAN ${row.ean} não existe no catálogo.` }
  const { model, category, product } = found
  const colors = visibleColors(model)
  if (!colors.length) return { ok: false, message: `${model.nome}: não tem cores disponíveis.` }
  const numbers = colors.map((c) => c.numero).join(', ')
  let color
  if (row.color === null) {
    if (colors.length > 1)
      return { ok: false, message: `${model.nome}: indique a cor. As cores são ${numbers}.` }
    color = colors[0]
  } else {
    color = colors.find((c) => c.numero === row.color)
    if (!color)
      return {
        ok: false,
        message: `${model.nome}: a cor ${row.color} não existe. As cores são ${numbers}.`,
      }
  }
  const { step, min } = resolveCartQtyRules(category)
  const { value, notice } = adjustQuantity(row.quantity, min, step)
  const item = cartItemFor({ model, category, product, color, quantity: value })
  const measure = item.altura || item.dimensoes
  const label = [
    model.nome,
    measure && (item.altura ? measure : `${measure} cm`),
    `Cor ${color.numero}${color.nome ? ` (${color.nome})` : ''}`,
  ]
    .filter(Boolean)
    .join(' · ')
  return { ok: true, item, color, notice, label: `${label}: ${value} un.` }
}
