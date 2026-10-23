import { ref } from 'vue'

import { apiGet } from '@/lib/api'
import {
  catalogueModelsForCategory,
  modelDetailAuto,
  modelDetailForSlugs,
  modelDetailForTipo,
} from '@/lib/catalogSupabase'
import { getCatalogMeta, setLiveCatalogMeta } from '@/lib/catalogMeta'
import { supabaseConfigured } from '@/lib/supabase'

import {
  formatBadgeLabel,
  formatPickerLabel,
  isSingleProductMode,
  storefrontContextForModel,
  prettyCatalogLabel,
} from '@/lib/storefrontFormat'
import { parseDimensions } from '@/lib/images'

const metaCache = ref(null)
let metaInFlight = null
const LIST_CACHE_KEY = 'diomika_cat_models_v2'
// Só evita repetir o mesmo pedido em navegações seguidas; acima disto vai-se
// sempre buscar dados frescos (a cache rápida é a da Cloudflare). Uma cópia
// mais antiga só serve de recurso se a API falhar.
const LIST_FRESH_MS = 15 * 1000
const LIST_FALLBACK_MS = 24 * 60 * 60 * 1000

function listCacheId(tipo, categoryId, activeFilters) {
  return `${tipo}:${categoryId}:${JSON.stringify(activeFilters || {})}`
}

function readListCache(id, maxAgeMs = LIST_FRESH_MS) {
  if (typeof sessionStorage === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(LIST_CACHE_KEY)
    if (!raw) return null
    const bag = JSON.parse(raw)
    const row = bag?.[id]
    if (!row?.data || !row?.at || Date.now() - row.at > maxAgeMs) return null
    return row.data
  } catch {
    return null
  }
}

function writeListCache(id, data) {
  if (typeof sessionStorage === 'undefined' || !Array.isArray(data)) return
  try {
    const raw = sessionStorage.getItem(LIST_CACHE_KEY)
    const bag = raw ? JSON.parse(raw) : {}
    bag[id] = { data, at: Date.now() }
    const keys = Object.keys(bag)
    if (keys.length > 80) {
      keys.sort((a, b) => (bag[a].at || 0) - (bag[b].at || 0))
      keys.slice(0, keys.length - 60).forEach((k) => delete bag[k])
    }
    sessionStorage.setItem(LIST_CACHE_KEY, JSON.stringify(bag))
  } catch {
    /* quota */
  }
}

export function useCatalog() {
  const loadMeta = async (force = false) => {
    if (metaCache.value && !force) return metaCache.value
    // App.vue e a página pedem o meta ao mesmo tempo no arranque — partilham o pedido.
    if (!metaInFlight || force) {
      metaInFlight = (async () => {
        try {
          const data = await apiGet('/catalogo/meta')
          metaCache.value = data
          setLiveCatalogMeta(data)
        } catch {
          metaCache.value = getCatalogMeta()
        } finally {
          metaInFlight = null
        }
        return metaCache.value
      })()
    }
    return metaInFlight
  }

  const resolveTipoConfig = (tipo) => {
    if (!tipo) return null
    const meta = metaCache.value || getCatalogMeta()
    const physical = (meta?.catalog_types || []).find((t) => t.tipo === tipo)
    if (physical) return physical
    return (meta?.aggregated_categories || []).find((t) => t.tipo === tipo) || null
  }

  const tipoConfig = (tipo) => resolveTipoConfig(tipo)

  const storefrontMode = (tipo) => tipoConfig(tipo)?.storefront_mode || 'variantes'

  const isAssentoMode = (tipo) => storefrontMode(tipo) === 'assento'

  const isAggregatedMode = (tipo) => {
    if (storefrontMode(tipo) === 'aggregado') return true
    return Boolean((metaCache.value?.aggregated_categories || []).find((t) => t.tipo === tipo))
  }

  const storefrontContext = (tipo, model = null) => {
    if (model?._storefront) return model._storefront
    const physicalTipo = model?._tipo_catalogo || tipo
    return storefrontContextForModel(model, tipoConfig(physicalTipo))
  }

  const badgeLabel = (model, tipo) => {
    const ctx = storefrontContext(tipo, model)
    const fam = model?._familia_label
    const base = formatBadgeLabel(ctx.badge, model)
    if (fam && isAggregatedMode(tipo)) return fam
    return base || fam || ''
  }

  const buildFilterQuery = (tipo, activeFilters) => {
    const params = new URLSearchParams()
    for (const [field, value] of Object.entries(activeFilters || {})) {
      if (value) params.set(`filter_${field}`, value)
    }
    const qs = params.toString()
    return qs ? `?${qs}` : ''
  }

  const fetchCategoryModels = async (tipo, categoryId, activeFilters = null, { force = false } = {}) => {
    await loadMeta()

    const cacheId = listCacheId(tipo, categoryId, activeFilters)
    const cached = !force ? readListCache(cacheId) : null

    let url = `/catalogo/${encodeURIComponent(tipo)}/modelos-catalogo/${categoryId}`
    url += buildFilterQuery(tipo, activeFilters)

    const loadFresh = async () => {
      try {
        return await apiGet(url)
      } catch (apiErr) {
        if (supabaseConfigured) {
          return catalogueModelsForCategory(tipo, categoryId, { filters: activeFilters || {} })
        }
        throw apiErr
      }
    }

    if (cached) return cached

    try {
      const data = await loadFresh()
      writeListCache(cacheId, data)
      return data
    } catch (err) {
      // Resiliência: sem API nem Supabase, mostra a última lista vista nesta sessão.
      const fallback = readListCache(cacheId, LIST_FALLBACK_MS)
      if (fallback) return fallback
      throw err
    }
  }

  const searchCatalog = async (query, { limit = 40 } = {}) => {
    const q = String(query || '').trim()
    if (q.length < 2) return []
    return apiGet(`/catalogo/search?q=${encodeURIComponent(q)}&limit=${limit}`)
  }

  const fetchModelDetail = async ({ categorySlug = null, modelSlug = null, modelId = null, tipo = null } = {}) => {
    if (categorySlug && modelSlug) {
      try {
        const resolvedTipo =
          tipo || (await apiGet(`/categorias/slug/${encodeURIComponent(categorySlug)}`)).tipo_catalogo
        const data = await apiGet(
          `/catalogo/${encodeURIComponent(resolvedTipo)}/modelo-detalhe/slug/${encodeURIComponent(categorySlug)}/${encodeURIComponent(modelSlug)}`,
        )
        return {
          ...data,
          _tipo_catalogo: data._tipo_catalogo || resolvedTipo,
          _storefront_mode: data._storefront_mode || storefrontMode(data._tipo_catalogo || resolvedTipo),
        }
      } catch (apiErr) {
        if (!supabaseConfigured) throw apiErr
      }
    }

    if (tipo && modelId) {
      try {
        const data = await apiGet(`/catalogo/${encodeURIComponent(tipo)}/modelo-detalhe/${modelId}`)
        return {
          ...data,
          _tipo_catalogo: tipo,
          _storefront_mode: data._storefront_mode || storefrontMode(tipo),
        }
      } catch (apiErr) {
        if (!supabaseConfigured) throw apiErr
      }
    }

    if (modelId) {
      try {
        return await apiGet(`/catalogo/modelo-detalhe/${modelId}`)
      } catch (apiErr) {
        if (!supabaseConfigured) throw apiErr
      }
    }

    if (supabaseConfigured) {
      let data = null
      if (categorySlug && modelSlug) {
        data = await modelDetailForSlugs(categorySlug, modelSlug, tipo)
      } else if (modelId) {
        data = tipo
          ? await modelDetailForTipo(tipo, modelId)
          : await modelDetailAuto(modelId)
      }
      if (!data) throw new Error('Modelo não encontrado.')
      const resolvedTipo = data._tipo_catalogo || tipo
      return {
        ...data,
        _tipo_catalogo: resolvedTipo,
        _storefront_mode:
          data._storefront_mode || (resolvedTipo ? storefrontMode(resolvedTipo) : data._storefront_mode),
      }
    }

    throw new Error('Modelo não encontrado.')
  }

  const buildPickerOptions = (model, ctx) => {
    if (!model || !ctx) return []

    const withEan = (rows) => {
      const list = Array.isArray(rows) ? rows : rows ? [rows] : []
      return list.filter((p) => p && String(p.ean || '').trim())
    }

    if (ctx.mode === 'unico') {
      const pt = ctx.product_table
      const product = withEan(model[pt])[0]
      if (!product) return []
      return [
        {
          id: product.id,
          value: product,
          raw: product.ean,
          label: 'Referência',
          product,
        },
      ]
    }

    if (model.tipo_oculo === 'leitura') {
      const pt = ctx.product_table
      const product = withEan(model[pt])[0]
      if (!product) return []
      return [
        {
          id: product.id,
          value: product,
          raw: product.ean,
          label: 'Sortido',
          product,
        },
      ]
    }

    const picker = ctx.picker
    if (!picker) return []

    const productTable = ctx.product_table

    if (picker.source === 'model') {
      return (model[picker.field] || []).map((value) => ({
        id: value,
        value,
        label: formatPickerLabel(picker, value),
        raw: value,
      }))
    }

    const variants = withEan(model[productTable])
    const options = variants
      .filter((product) => product[picker.field] != null && product[picker.field] !== '')
      .map((product) => ({
        id: product.id,
        value: product,
        raw: product[picker.field],
        label: formatPickerLabel(picker, product[picker.field]),
        product,
      }))

    if (picker.format === 'dimensions') {
      options.sort((a, b) => parseDimensions(a.raw) - parseDimensions(b.raw))
    }

    return options
  }

  const activeProduct = (model, ctx, selectedOption) => {
    if (!model || !ctx) return null
    if (isSingleProductMode(ctx)) {
      const pt = ctx.product_table
      const products = Array.isArray(model[pt]) ? model[pt] : model[pt] ? [model[pt]] : []
      return selectedOption?.value || products[0] || null
    }
    return selectedOption?.value || null
  }

  const filterDefinitionsForTipo = (tipo) => {
    const cfg = resolveTipoConfig(tipo)
    if (cfg?.storefront_filters?.length) return cfg.storefront_filters
    return []
  }

  const filterOptionsForField = (filterDef) => {
    if (!filterDef) return [{ value: '', label: 'Todos' }]
    return [
      { value: '', label: 'Todos' },
      ...(filterDef.options || []).map((v) => ({
        value: v,
        label: filterDef.labels?.[v] || prettyCatalogLabel(v),
      })),
    ]
  }


  const prefetchCategoryModels = (tipo, categoryId, activeFilters = null) => {
    void fetchCategoryModels(tipo, categoryId, activeFilters).catch(() => {})
  }

  return {
    metaCache,
    loadMeta,
    tipoConfig,
    storefrontMode,
    isAssentoMode,
    isAggregatedMode,
    storefrontContext,
    badgeLabel,
    fetchCategoryModels,
    prefetchCategoryModels,
    searchCatalog,
    fetchModelDetail,
    buildPickerOptions,
    activeProduct,
    filterDefinitionsForTipo,
    filterOptionsForField,
  }
}
