const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export function isUuid(value) {
  return UUID_RE.test(String(value || '').trim())
}

/** Slug legível para URLs — preferir nome/slug público, nunca UUID. */
export function slugifyName(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

export function categorySlug(category) {
  const explicit = String(category?.slug || '').trim()
  if (explicit && !isUuid(explicit)) return explicit
  const fromName = slugifyName(category?.nome)
  if (fromName) return fromName
  return ''
}

export function modelSlug(model) {
  const fromName = slugifyName(model?.nome)
  if (fromName) return fromName
  const explicit = String(model?.slug || '').trim()
  if (explicit && !isUuid(explicit)) return explicit
  return ''
}

/** Rota canónica da listagem de modelos numa categoria. */
export function categoryProductsRoute(category) {
  const slug = categorySlug(category)
  if (!slug) return { name: 'categories' }
  return { name: 'products', params: { categorySlug: slug } }
}

/** Rota canónica do detalhe de um modelo. */
export function modelDetailRoute(category, model) {
  const catSlug = categorySlug(category)
  const modSlug = modelSlug(model)
  if (!catSlug || !modSlug) return { name: 'categories' }
  const query = {}
  if (category?.tipo_catalogo === 'material_cozinha' && model?._tipo_catalogo) {
    query.tipo = model._tipo_catalogo
  }
  return {
    name: 'product-detail',
    params: { categorySlug: catSlug, modelSlug: modSlug },
    ...(Object.keys(query).length ? { query } : {}),
  }
}
