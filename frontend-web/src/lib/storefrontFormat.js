import { PHYSICAL_CATALOG_TABLES } from '@/lib/catalogMeta'

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

  if (Array.isArray(value)) {
    return value.join(', ')
  }

  return String(value)
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
  return model?._storefront || {
    mode: tipoConfig?.storefront_mode || 'variantes',
    // product_table aqui tem de ser o nome físico real (a chave sob a qual
    // as variantes vêm embutidas na linha) — nunca o nome virtual de
    // catalog_types, que só serve o encaminhamento do backoffice.
    product_table: PHYSICAL_CATALOG_TABLES.variants,
    picker: tipoConfig?.storefront_picker,
    specs: tipoConfig?.storefront_specs || [],
    badge: tipoConfig?.storefront_badge,
  }
}

export function isSingleProductMode(ctx) {
  if (ctx?.mode === 'unico') return true
  return ctx?.picker?.source === 'model'
}
