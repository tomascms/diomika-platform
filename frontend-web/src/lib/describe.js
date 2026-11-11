/**
 * Textos do catálogo escritos a partir dos dados de um modelo (auditoria: FE-03, RP-02, SEO-02, BR-04, FE-16).
 *
 * Servem a loja (vistas de produto e de categoria) e o pré-render (scripts/prerender-seo.mjs, em Node), por isso
 * é JavaScript simples: sem o alias «@» nem APIs do browser. A página que o visitante vê e a que o Google lê
 * saem da mesma função, e nunca mostram o «Sem descrição» dos dados antigos.
 */
import { MIN_ORDER } from './constants.js'

/** Primeira letra maiúscula, o resto como está: «Material de Cozinha» não passa a «Material De Cozinha». */
export function pretty(text) {
  const s = String(text ?? '').trim()
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''
}

/** A descrição que alguém escreveu. O texto «Sem descrição» dos dados antigos conta como vazio. */
export function realDescription(text) {
  const s = String(text ?? '').trim()
  return s && !/^sem descri/i.test(s) ? s : ''
}

const areaOf = (dimension) => {
  const match = /^(\d+)x(\d+)$/.exec(String(dimension).trim())
  return match ? Number(match[1]) * Number(match[2]) : Infinity
}

/** Medidas «CxL» por ordem de área, como os botões da ficha. O que não é medida fica no fim, como veio. */
export function sortDimensions(list) {
  return (list || [])
    .map((value, index) => ({ value, index, area: areaOf(value) }))
    .sort((a, b) => a.area - b.area || a.index - b.index)
    .map((entry) => entry.value)
}

/** Rótulo de uma especificação na loja: sem as notas do backoffice («Composição (%) — igual para todas as cores»). */
export function storeLabel(label) {
  return String(label ?? '')
    .replace(/\s+[—–]\s+.*$/, '')
    .replace(/\s*\(%\)/, '')
    .trim()
}

/** «a», «a e b», «a, b e c». */
const joinList = (items) =>
  items.length < 2
    ? items.join('')
    : `${items.slice(0, -1).join(', ')} e ${items[items.length - 1]}`

const productRows = (model) => {
  const table = model?._storefront?.product_table
  const rows = table ? model[table] : null
  return Array.isArray(rows) ? rows : rows ? [rows] : []
}

/** O que o selector da ficha oferece (medidas, alturas), pela mesma ordem. */
function pickerValues(model) {
  const picker = model?._storefront?.picker
  if (!picker?.field) return []
  const raw =
    picker.source === 'model'
      ? model[picker.field]
      : productRows(model)
          .filter((row) => String(row?.ean || '').trim())
          .map((row) => row[picker.field])
  const values = [
    ...new Set((Array.isArray(raw) ? raw : []).map((v) => String(v ?? '').trim()).filter(Boolean)),
  ]
  return picker.format === 'dimensions' ? sortDimensions(values) : values
}

/** O que o selector da ficha escolhe, no singular e no plural: medida(s), altura(s), opção/opções. */
export function pickerNoun(picker) {
  if (picker?.format === 'dimensions') return ['medida', 'medidas']
  return picker?.field === 'altura' ? ['altura', 'alturas'] : ['opção', 'opções']
}

const SIZES_LISTED_UP_TO = 4

function sizesPhrase(model) {
  const picker = model._storefront.picker
  const sizes = pickerValues(model)
  if (!sizes.length) return ''
  const dimensions = picker.format === 'dimensions'
  const [one, many] = pickerNoun(picker)
  const noun = `${sizes.length} ${sizes.length === 1 ? one : many}`
  if (sizes.length <= SIZES_LISTED_UP_TO)
    return `${noun} (${joinList(sizes)}${dimensions ? picker.suffix || '' : ''})`
  // Muitas medidas: o intervalo diz o essencial, a lista está nos botões da ficha.
  return dimensions
    ? `${noun} (de ${sizes[0]} a ${sizes[sizes.length - 1]}${picker.suffix || ''})`
    : noun
}

// Só as especificações que dizem de que é feito o artigo; cuidados, gramagem, origem, etc. ficam na lista de especificações.
const MATERIAL_FIELD = /^material/

/**
 * Frase com o que se sabe do modelo: tipo, composição ou materiais e em que medidas e cores se vende.
 * «Tipo: Decorativa. Composição: 100% Poliester. Disponível em 3 medidas (35x50, 45x45 e 60x60 cm) e em 5 cores.»
 * Só afirma o que está nos dados e dá '' se não houver nada para dizer (uma só cor não é informação).
 */
export function describeModel(model) {
  const storefront = model?._storefront
  if (!storefront) return ''
  const clauses = []

  const badge = storefront.badge
  const kind = badge?.field ? model[badge.field] : null
  if (kind)
    clauses.push(`Tipo: ${badge.labels?.[kind] || pretty(String(kind).replace(/_/g, ' '))}.`)

  for (const spec of storefront.specs || []) {
    const value = model[spec.field]
    if (spec.widget === 'composition' && value && typeof value === 'object') {
      const parts = Object.entries(value).map(([material, percent]) => `${percent}% ${material}`)
      if (parts.length) clauses.push(`${storeLabel(spec.label)}: ${joinList(parts)}.`)
    } else if (MATERIAL_FIELD.test(spec.field) && typeof value === 'string' && value.trim()) {
      clauses.push(`${storeLabel(spec.label)}: ${value.trim()}.`)
    }
  }

  const colours = (model.modelo_cores || []).filter((c) => c && c.visibilidade !== false).length
  const available = [
    storefront.picker ? sizesPhrase(model) : '',
    colours > 1 ? `${colours} cores` : '',
  ].filter(Boolean)
  if (available.length) clauses.push(`Disponível em ${available.join(' e em ')}.`)

  return clauses.join(' ')
}

/** Corta em palavra inteira, com reticências só se cortar (a meta description cabe em ~160 caracteres). */
export function clip(text, max = 160) {
  const s = String(text ?? '')
    .replace(/\s+/g, ' ')
    .trim()
  if (s.length <= max) return s
  const head = s.slice(0, max - 1)
  const space = head.lastIndexOf(' ')
  return `${(space > 0 ? head.slice(0, space) : head).replace(/[\s,;:.—-]+$/, '')}…`
}

const ORDER_CTA = 'Peça orçamento à Diomika.'

/**
 * Título e descrição de uma página de modelo (loja e pré-render): «Foglia — Almofada», e a descrição que o
 * cliente escreveu, ou a gerada a partir das especificações, ou uma frase genérica com o nome e a categoria.
 */
export function modelMeta(model, categoryName = '') {
  const name = String(model?.nome ?? '').trim()
  const category = String(categoryName ?? '').trim()
  const body =
    realDescription(model?.descricao) ||
    describeModel(model) ||
    (category ? `${name} — ${category.toLowerCase()}.` : `${name}.`)
  return {
    title: category ? `${name} — ${category}` : name,
    description: clip(`${body} ${ORDER_CTA}`),
  }
}

/** Descrição de uma página de categoria. `count` (modelos mostráveis) só entra se se souber. */
export function categoryMeta(categoryName, count) {
  const models = Number.isInteger(count)
    ? `${count} ${count === 1 ? 'modelo' : 'modelos'}`
    : 'modelos'
  return `${categoryName}: ${models} em várias cores e medidas. ${ORDER_CTA.slice(0, -1)} — pedido mínimo ${MIN_ORDER.replaceAll(' ', ' ')}.`
}
