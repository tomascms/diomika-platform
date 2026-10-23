import { ensureSupabase, supabaseConfigured } from '@/lib/supabase'
import { PHYSICAL_CATALOG_TABLES, getCatalogMeta, getTipoConfig } from '@/lib/catalogMeta'

// Esquema unificado: 3 tabelas físicas partilhadas por todas as categorias,
// discriminadas por `tipo_catalogo`. Isto é o caminho de reserva usado só
// quando a API do backend está inacessível (ver useCatalog.js) — fala
// directamente com o Supabase a partir do browser, por isso tem de conhecer
// o esquema real, não os nomes virtuais que catalog_types usa para o
// backoffice encaminhar pedidos a /admin/crud/{tabela}.
const MODELS_TABLE = PHYSICAL_CATALOG_TABLES.models
const VARIANTS_TABLE = PHYSICAL_CATALOG_TABLES.variants
const COLORS_TABLE = PHYSICAL_CATALOG_TABLES.colors
const PRODUCT_SELECT = 'id, ean, barcode_url, visibilidade, attributes'

const CATEGORY_FIELDS = 'id,nome,slug,imagem,tipo_catalogo,carrinho_step,carrinho_min'
const CATEGORY_EMBED = 'id, nome, slug, carrinho_step, carrinho_min, tipo_catalogo'

async function db() {
  if (!supabaseConfigured) throw new Error('Supabase não configurado.')
  const client = await ensureSupabase()
  if (!client) throw new Error('Supabase não configurado.')
  return client
}

function isVisible(row) {
  return row && row.visibilidade !== false
}

function hasEan(row) {
  return Boolean(String(row?.ean || '').trim())
}

function visibleProducts(rows) {
  const list = Array.isArray(rows) ? rows : rows ? [rows] : []
  // Sem EAN o produto não é encomendável — não conta para a loja.
  return list.filter((row) => isVisible(row) && hasEan(row))
}

function normalizeStringList(value) {
  if (value == null) return []
  if (Array.isArray(value)) {
    return [...value].map((v) => String(v).trim()).filter(Boolean).sort()
  }
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      if (Array.isArray(parsed)) {
        return parsed.map((v) => String(v).trim()).filter(Boolean).sort()
      }
    } catch {
      /* continua */
    }
    const trimmed = value.trim()
    return trimmed ? [trimmed] : []
  }
  return []
}

/** Copia os campos de `attributes` (jsonb) também para o nível de topo —
 * mantém a mesma forma que o resto do código (e a API do backend) já espera
 * (`product.dimensoes`, `model.tipo_oculo`, ...), em vez de cada sítio ter de
 * saber que esses campos vivem dentro de `attributes`. */
function flattenAttrs(row) {
  if (row && row.attributes && typeof row.attributes === 'object') {
    return { ...row.attributes, ...row }
  }
  return row
}

function attachStorefrontFields(data, cfg) {
  const picker = cfg.storefront_picker
  if (picker?.source === 'model' && picker.field && picker.field in data) {
    data[picker.field] = normalizeStringList(data[picker.field])
  }
  if ('dimensoes' in data) {
    data.dimensoes = normalizeStringList(data.dimensoes)
  }
  if ('alturas' in data) {
    data.alturas = normalizeStringList(data.alturas)
  }
  return data
}

function modeloCores(data) {
  const cores = (data.modelo_cores || []).filter(isVisible)
  cores.sort((a, b) => (a.numero || 0) - (b.numero || 0))
  return cores
}

async function attachModeloCores(rows) {
  if (!rows?.length) return

  const supabase = await db()
  const modelIds = rows.map((row) => String(row.id)).filter(Boolean)
  const coresByModel = Object.fromEntries(modelIds.map((id) => [id, []]))

  if (modelIds.length) {
    const { data: direct } = await supabase
      .from(COLORS_TABLE)
      .select('id_modelo, numero, nome, imagem, visibilidade')
      .in('id_modelo', modelIds)

    for (const cor of direct || []) {
      const mid = String(cor.id_modelo || '')
      if (coresByModel[mid]) coresByModel[mid].push(cor)
    }
  }

  for (const row of rows) {
    const mid = String(row.id || '')
    row.modelo_cores = modeloCores({ modelo_cores: coresByModel[mid] || [] })
  }
}

function storefrontContext(cfg) {
  return {
    mode: cfg.storefront_mode || 'variantes',
    product_table: VARIANTS_TABLE,
    picker: cfg.storefront_picker,
    specs: cfg.storefront_specs || [],
    badge: cfg.storefront_badge,
  }
}

function finalizeModelRow(row, cfg) {
  const pt = VARIANTS_TABLE
  const mode = cfg.storefront_mode || 'variantes'
  // Sem produtos com EAN ou sem cores → não aparece na loja (evita barcodes / ficha inválidos).
  if (!modeloCores(row).length) return null
  const products = visibleProducts(row[pt]).map(flattenAttrs)

  if (mode === 'unico') {
    if (!products.length) return null
    row[pt] = products.length === 1 ? products[0] : products
  } else if (mode === 'assento') {
    if (!products.length) return null
    products.sort((a, b) => String(a.altura || '').localeCompare(String(b.altura || '')))
    row[pt] = products
  } else {
    if (!products.length) return null
    products.sort((a, b) =>
      String(a.dimensoes || a.segmento || '').localeCompare(String(b.dimensoes || b.segmento || '')),
    )
    row[pt] = products
  }

  row._tipo_catalogo = cfg.tipo
  row._storefront = storefrontContext(cfg)
  row._storefront_mode = mode
  return row
}

/** Campos que vivem na variante (produto), não no modelo — não filtrar com .eq na tabela do modelo. */
const PRODUCT_FILTER_FIELDS = new Set(['dimensoes', 'altura', 'segmento', 'ean'])

function splitFilters(filters = {}) {
  const modelFilters = {}
  const productFilters = {}
  for (const [field, value] of Object.entries(filters || {})) {
    if (!field || field.startsWith('_') || value == null || String(value).trim() === '') continue
    if (PRODUCT_FILTER_FIELDS.has(field)) productFilters[field] = String(value)
    else modelFilters[field] = String(value)
  }
  return { modelFilters, productFilters }
}

function matchesProductFilters(row, productFilters) {
  const entries = Object.entries(productFilters || {})
  if (!entries.length) return true
  const raw = row?.[VARIANTS_TABLE]
  const products = Array.isArray(raw) ? raw : raw ? [raw] : []
  return products.some((p) =>
    entries.every(([field, value]) => String(p?.[field] ?? '') === value),
  )
}

export { getCatalogMeta } from '@/lib/catalogMeta'

export async function listCategories() {
  const supabase = await db()

  const { data, error } = await supabase
    .from('categories')
    .select(CATEGORY_FIELDS)
    .eq('visibilidade', true)
    .order('nome')

  if (error) throw new Error(error.message)
  return data || []
}

export async function getCategoryById(id) {
  const supabase = await db()

  const { data, error } = await supabase
    .from('categories')
    .select(CATEGORY_FIELDS)
    .eq('id', id)
    .eq('visibilidade', true)
    .maybeSingle()

  if (error) throw new Error(error.message)
  if (!data) throw new Error('Categoria não encontrada.')
  return data
}

export async function getCategoryBySlug(slug) {
  const supabase = await db()

  const key = String(slug || '').trim()
  if (!key) throw new Error('Categoria não encontrada.')

  const { data, error } = await supabase
    .from('categories')
    .select(CATEGORY_FIELDS)
    .eq('slug', key)
    .eq('visibilidade', true)
    .maybeSingle()

  if (error) throw new Error(error.message)
  if (data) return data

  const { data: byName, error: nameError } = await supabase
    .from('categories')
    .select(CATEGORY_FIELDS)
    .ilike('nome', key)
    .eq('visibilidade', true)
    .maybeSingle()

  if (nameError) throw new Error(nameError.message)
  if (!byName) throw new Error('Categoria não encontrada.')
  return byName
}

export async function resolveCategoryParam(param) {
  const key = String(param || '').trim()
  if (!key) throw new Error('Categoria não encontrada.')
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(key)) {
    return getCategoryById(key)
  }
  return getCategoryBySlug(key)
}

async function requirePublicCategory(categoryId) {
  const supabase = await db()
  const { data, error } = await supabase
    .from('categories')
    .select('id,visibilidade')
    .eq('id', categoryId)
    .maybeSingle()
  if (error) throw new Error(error.message)
  return isVisible(data)
}

export async function catalogueModelsForTipo(tipo, categoryId, { filters = {}, filterField = null, filterValue = null } = {}) {
  const supabase = await db()

  const cfg = getTipoConfig(tipo)
  if (!cfg) return []
  if (!(await requirePublicCategory(categoryId))) return []

  const activeFilters = { ...filters }
  if (filterField && filterValue) activeFilters[filterField] = filterValue
  const { modelFilters, productFilters } = splitFilters(activeFilters)

  let query = supabase
    .from(MODELS_TABLE)
    .select(`*, categories(${CATEGORY_EMBED}), ${VARIANTS_TABLE}(${PRODUCT_SELECT})`)
    .eq('id_categoria', categoryId)
    .eq('tipo_catalogo', tipo)
    .eq('visibilidade', true)

  for (const [field, value] of Object.entries(modelFilters)) {
    query = query.eq(`attributes->>${field}`, value)
  }

  const { data, error } = await query.order('nome')
  if (error) throw new Error(error.message)

  await attachModeloCores(data || [])

  const out = []
  for (const raw of data || []) {
    const row = attachStorefrontFields(flattenAttrs({ ...raw }), cfg)
    row.modelo_cores = modeloCores(row)
    const finalized = finalizeModelRow(row, { ...cfg, tipo })
    if (!finalized) continue
    if (!matchesProductFilters(finalized, productFilters)) continue
    out.push(finalized)
  }
  return out
}

export async function catalogueModelsForCategory(tipo, categoryId, { filters = {} } = {}) {
  const cfg = getTipoConfig(tipo)
  if (!cfg) return []

  if (cfg.aggregated_tipos?.length) {
    const family = filters._tipo_catalogo
    const dbFilters = Object.fromEntries(
      Object.entries(filters).filter(([key]) => !key.startsWith('_')),
    )
    const chunks = await Promise.all(
      cfg.aggregated_tipos.map(async (physical) => {
        if (family && physical !== family) return []
        const rows = await catalogueModelsForTipo(physical, categoryId, { filters: dbFilters })
        return rows.map((row) => {
          row._tipo_catalogo = physical
          row._category_tipo = tipo
          row._familia_label = getTipoConfig(physical)?.label || physical
          return row
        })
      }),
    )
    const out = chunks.flat()
    out.sort((a, b) => String(a.nome || '').localeCompare(String(b.nome || '')))
    return out
  }

  return catalogueModelsForTipo(tipo, categoryId, { filters })
}

export async function modelDetailForTipo(tipo, modelId) {
  const supabase = await db()

  const cfg = getTipoConfig(tipo)
  if (!cfg) return null

  const { data, error } = await supabase
    .from(MODELS_TABLE)
    .select(`*, categories(${CATEGORY_EMBED},visibilidade), ${VARIANTS_TABLE}(*)`)
    .eq('id', modelId)
    .eq('tipo_catalogo', tipo)
    .maybeSingle()

  if (error) throw new Error(error.message)
  return await finalizeModelDetailRow(data, { ...cfg, tipo })
}

export async function modelDetailForSlugs(categorySlug, modelSlug, tipo = null) {
  if (!supabaseConfigured) throw new Error('Supabase não configurado.')

  const category = await resolveCategoryParam(categorySlug)
  const resolvedTipo = tipo || category.tipo_catalogo
  const cfg = getTipoConfig(resolvedTipo)
  if (!cfg) return null

  const modKey = String(modelSlug || '').trim()
  if (!modKey) return null

  if (cfg.aggregated_tipos?.length) {
    const tipos = tipo ? [tipo] : cfg.aggregated_tipos
    for (const physical of tipos) {
      const physicalCfg = getTipoConfig(physical)
      if (!physicalCfg) continue
      const data = await _lookupModelInTable(physical, category.id, modKey)
      if (data) {
        const row = await finalizeModelDetailRow(data, { ...physicalCfg, tipo: physical })
        if (row) {
          row._tipo_catalogo = physical
          row._category_tipo = resolvedTipo
          row._familia_label = physicalCfg.label || physical
        }
        return row
      }
    }
    return null
  }

  const data = await _lookupModelInTable(resolvedTipo, category.id, modKey)
  return await finalizeModelDetailRow(data, { ...cfg, tipo: resolvedTipo })
}

async function _lookupModelInTable(tipo, categoryId, modKey) {
  const supabase = await db()
  const isUuidKey = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(modKey)
  const baseSelect = `*, categories(${CATEGORY_EMBED},visibilidade), ${VARIANTS_TABLE}(*)`
  const baseFilters = (q) =>
    q.eq('id_categoria', categoryId).eq('tipo_catalogo', tipo).eq('visibilidade', true)

  if (isUuidKey) {
    const { data, error } = await baseFilters(supabase.from(MODELS_TABLE).select(baseSelect)).eq('id', modKey).maybeSingle()
    if (error) throw new Error(error.message)
    return data
  }

  const { data: rows, error } = await baseFilters(supabase.from(MODELS_TABLE).select(baseSelect))
    .or(`slug.eq.${modKey},nome.ilike.${modKey}`)
    .limit(1)
  if (error) throw new Error(error.message)
  return rows?.[0] || null
}

async function finalizeModelDetailRow(data, cfg) {
  if (!data || !isVisible(data)) return null
  if (data.categories && !isVisible(data.categories)) return null

  if (data.categories) {
    const { visibilidade: _v, ...publicCat } = data.categories
    data.categories = publicCat
  }

  await attachModeloCores([data])
  const row = attachStorefrontFields(flattenAttrs({ ...data }), cfg)
  row.modelo_cores = modeloCores(row)
  return finalizeModelRow(row, cfg)
}

export async function modelDetailAuto(modelId) {
  // Esquema unificado: tipo_catalogo já é uma coluna do próprio modelo —
  // 1 query, não 1 tentativa por família de catálogo.
  const supabase = await db()
  const { data, error } = await supabase
    .from(MODELS_TABLE)
    .select('tipo_catalogo')
    .eq('id', modelId)
    .maybeSingle()
  if (error || !data?.tipo_catalogo) return null
  if (!getTipoConfig(data.tipo_catalogo)) return null
  return modelDetailForTipo(data.tipo_catalogo, modelId)
}
