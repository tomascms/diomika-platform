import { PHYSICAL_CATALOG_TABLES } from './catalogMeta.js'
import { sortDimensions } from './describe.js'

export function formatStorefrontValue(spec, value) {
  if (value == null || value === '') return null

  if (spec.widget === 'enum') {
    return spec.enum_labels?.[value] || value
  }

  if (spec.widget === 'composition' && typeof value === 'object' && !Array.isArray(value)) {
    return Object.entries(value)
      .map(([material, percent]) => `${percent}% ${material}`)
      .join(', ')
  }

  if (spec.widget === 'boolean') {
    return value ? 'Sim' : 'Não'
  }

  // Pela mesma ordem dos botões de medida da ficha (FE-16): a BD guarda-as pela ordem em que foram escritas.
  if (spec.widget === 'dimension_list' && Array.isArray(value)) {
    return sortDimensions(value).join(', ')
  }

  if (Array.isArray(value)) {
    return value.join(', ')
  }

  return String(value)
}

/**
 * As linhas da lista de especificações de um modelo (ficha e catálogo para imprimir): só as que têm valor.
 * `specs` é o `_storefront.specs` que a API manda; um campo novo da família aparece sem código por campo.
 */
export function specRows(model, specs) {
  return (specs || [])
    .map((spec) => {
      const raw = model?.[spec.field]
      const composition = spec.widget === 'composition' && raw && typeof raw === 'object'
      return {
        ...spec,
        raw,
        display: formatStorefrontValue(spec, raw),
        isComposition: Boolean(composition),
        compositionEntries: composition ? Object.entries(raw) : [],
      }
    })
    .filter((row) => row.display || row.compositionEntries.length)
}

/** Todos os EAN que aparecem num modelo ou numa linha de produto, a qualquer profundidade (a pesquisa por EAN usa-os). */
export function collectEans(value, found = []) {
  if (!value || typeof value !== 'object') return found
  if (Array.isArray(value)) {
    value.forEach((entry) => collectEans(entry, found))
    return found
  }
  for (const [key, entry] of Object.entries(value)) {
    if (key === 'ean' && entry != null) found.push(String(entry))
    else if (entry && typeof entry === 'object') collectEans(entry, found)
  }
  return found
}

/** Mostra-se na loja: visível, com um EAN e com uma cor visível (a mesma regra da lista de categoria e do pré-render). */
export function showableModel(model) {
  if (!model || model.visibilidade === false) return false
  const rows = [].concat(model[model._storefront?.product_table || 'product_variants'] ?? [])
  return (
    rows.some((row) => String(row?.ean ?? '').trim()) &&
    (model.modelo_cores || []).some((color) => color && color.visibilidade !== false)
  )
}

/**
 * As variantes de um modelo com EAN, para uma lista ou tabela: a medida («45x45 cm», «32mm»; vazia num artigo único)
 * e o EAN, pela mesma ordem dos botões da ficha.
 */
export function variantList(model) {
  const ctx = model?._storefront
  const rows = []
    .concat(model?.[ctx?.product_table || 'product_variants'] ?? [])
    .filter((row) => String(row?.ean ?? '').trim())
  const field = ctx?.picker?.source === 'products' ? ctx.picker.field : null
  if (!field) return rows.map((row) => ({ measure: '', ean: String(row.ean).trim() }))
  const dimensions = ctx.picker.format === 'dimensions'
  const values = rows.map((row) => String(row[field] ?? '').trim())
  const order = dimensions ? sortDimensions(values) : values
  return rows
    .map((row, i) => ({ row, value: values[i], rank: order.indexOf(values[i]) }))
    .sort((a, b) => a.rank - b.rank)
    .map(({ row, value }) => ({
      measure: value && dimensions ? `${value}${ctx.picker.suffix || ''}` : value,
      ean: String(row.ean).trim(),
    }))
}

export function formatPickerLabel(picker, rawValue) {
  if (rawValue == null || rawValue === '') return ''
  if (picker?.format === 'dimensions') {
    return `${rawValue}${picker.suffix || ''}`.trim()
  }
  return String(rawValue)
}

function prettyCatalogLabel(value) {
  const raw = String(value || '').trim()
  if (!raw) return ''
  return raw
    .split(/[\s_]+/)
    .map((part) => (part ? part.charAt(0).toUpperCase() + part.slice(1).toLowerCase() : ''))
    .filter(Boolean)
    .join(' ')
}

export { prettyCatalogLabel }

export function formatBadgeLabel(badge, model) {
  if (!badge || !model) return ''
  const val = model[badge.field]
  if (!val) return ''
  const mapped = badge.labels?.[val]
  return mapped || prettyCatalogLabel(val)
}

export function storefrontContextForModel(model, tipoConfig) {
  return (
    model?._storefront || {
      mode: tipoConfig?.storefront_mode || 'variantes',
      // product_table aqui tem de ser o nome físico real (a chave sob a qual
      // as variantes vêm embutidas na linha) — nunca o nome virtual de
      // catalog_types, que só serve o encaminhamento do backoffice.
      product_table: PHYSICAL_CATALOG_TABLES.variants,
      picker: tipoConfig?.storefront_picker,
      specs: tipoConfig?.storefront_specs || [],
      badge: tipoConfig?.storefront_badge,
    }
  )
}

export function isSingleProductMode(ctx) {
  if (ctx?.mode === 'unico') return true
  return ctx?.picker?.source === 'model'
}
