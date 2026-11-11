<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import Breadcrumbs from '@/components/Breadcrumbs.vue'
import ErrorState from '@/components/ErrorState.vue'
import SoftImage from '@/components/SoftImage.vue'
import { useCatalog } from '@/composables/useCatalog'
import { useCategories } from '@/composables/useCategories'
import { setNoindex, watchDynamicTitle } from '@/composables/usePageMeta'
import { ApiError } from '@/lib/api'
import { categoryMeta, pretty } from '@/lib/describe'
import { collectEans } from '@/lib/storefrontFormat'
import { errorKind } from '@/lib/errors'
import { categorySlug as slugOfCategory, modelDetailRoute } from '@/lib/catalogRoutes'
import {
  PLACEHOLDER,
  resolveImageUrl,
  resolveImageUrls,
  safeCssUrl,
  thumbUrl,
  IMG_CARD,
} from '@/lib/images'

const route = useRoute()
const catalog = useCatalog()
const { categories: knownCategories } = useCategories()

const products = ref([])
const loading = ref(true)
const error = ref(null) // null, 'not-found' (a categoria já não existe) ou 'unavailable' (o servidor não respondeu)
const categoryData = ref(null)
const modelCount = ref(null) // modelos mostráveis da categoria sem filtros (só então a meta description os conta)
const unfilteredModels = ref(null) // esses modelos: dizem que opções de filtro levam a algum modelo
const selectedFilters = ref({})
const localSearch = ref('')
const sortBy = ref('az')
const breadcrumbItems = ref([{ label: 'Início', to: { name: 'home' } }])

const catalogTipo = computed(() => categoryData.value?.tipo_catalogo || '')
const filterDefs = computed(() => {
  // Garantir recomputação quando /catalogo/meta chega da API.
  void catalog.metaCache.value
  return catalog.filterDefinitionsForTipo(catalogTipo.value) || []
})
const heroImageUrl = computed(() => safeCssUrl(categoryData.value?.imagem) || '')
// A capa só se vê a partir de 720 px, e com 320 px de largura: miniaturas, não o original (PERF-01).
const heroSrc = computed(() => thumbUrl(heroImageUrl.value, 480))
const heroSrcset = computed(() =>
  heroSrc.value !== heroImageUrl.value
    ? `${heroSrc.value} 480w, ${thumbUrl(heroImageUrl.value, 960)} 960w`
    : undefined,
)
const tipoLabel = (product) => catalog.badgeLabel(product, catalogTipo.value)

let fetchSeq = 0
function blankFilters(defs = filterDefs.value) {
  return Object.fromEntries((defs || []).filter((def) => def?.field).map((def) => [def.field, '']))
}

function resetPageControls() {
  selectedFilters.value = {}
  localSearch.value = ''
  sortBy.value = 'az'
}

function clearFilters() {
  resetPageControls()
  void fetchProducts({ silent: true })
}

function onFilterChange(field, value) {
  selectedFilters.value = {
    ...selectedFilters.value,
    [field]: value ?? '',
  }
  clearTimeout(filterTimer)
  filterTimer = setTimeout(() => void fetchProducts({ silent: true }), 250)
}

let filterTimer = null

// Título e descrição iguais aos que o pré-render escreve no HTML (lib/describe.js): o Google lê os mesmos depois do JavaScript.
watchDynamicTitle(
  () => [categoryData.value?.nome, modelCount.value, route.params.categorySlug],
  () => {
    const nome = pretty(categoryData.value?.nome)
    if (!nome) return null
    return {
      title: nome,
      description: categoryMeta(nome, modelCount.value ?? undefined),
      image: categoryData.value?.imagem || PLACEHOLDER,
      path: route.path, // sem a query (SEO-05)
    }
  },
)

// Uma categoria sem modelos ou que já não existe não se indexa (FE-05, RP-04): `modelCount` só se conhece sem filtros.
watch(
  () => error.value === 'not-found' || modelCount.value === 0,
  (empty) => setNoindex(empty),
)

function foldText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toLocaleLowerCase('pt')
}

function searchHaystack(product) {
  const cores = (product.modelo_cores || []).map((c) => c?.nome).filter(Boolean)
  const extras = [
    product.tipo,
    product.tipo_oculo,
    product.tipo_produto,
    product.material,
    product.subtipo,
    product._familia_label,
  ].filter(Boolean)
  return foldText(
    [product.nome, product.slug, ...extras, ...cores, ...collectEans(product)].join(' '),
  )
}

function modelMatchesClientFilters(product, filters) {
  const entries = Object.entries(filters || {}).filter(([, v]) => String(v ?? '').trim())
  if (!entries.length) return true
  return entries.every(([field, value]) => {
    const wanted = String(value)
    if (String(product?.[field] ?? '') === wanted) return true
    if (field === '_tipo_catalogo' && String(product?._tipo_catalogo || '') === wanted) return true
    const pt =
      product?._storefront?.product_table ||
      catalog.storefrontContext(catalogTipo.value, product)?.product_table
    if (!pt) return false
    const rows = Array.isArray(product[pt]) ? product[pt] : product[pt] ? [product[pt]] : []
    return rows.some((row) => String(row?.[field] ?? '') === wanted)
  })
}

/**
 * As opções de um filtro que levam a algum modelo da categoria: «Panos de cozinha» em Material de Cozinha dava 0 modelos
 * (RP-03). Até a lista chegar mostram-se todas, para o filtro não aparecer e empurrar a grelha.
 */
function filterOptions(filterDef) {
  const options = catalog.filterOptionsForField(filterDef).filter((item) => item.value !== '')
  const models = unfilteredModels.value
  if (!models) return options
  return options.filter((item) =>
    models.some((model) => modelMatchesClientFilters(model, { [filterDef.field]: item.value })),
  )
}

const visibleFilterDefs = computed(() =>
  filterDefs.value.filter((filterDef) => filterOptions(filterDef).length),
)

const displayedProducts = computed(() => {
  const query = foldText(localSearch.value.trim())
  const active = Object.fromEntries(
    Object.entries(selectedFilters.value || {}).filter(([, v]) => String(v ?? '').trim()),
  )
  const filtered = products.value.filter((product) => {
    if (!modelMatchesClientFilters(product, active)) return false
    if (!query) return true
    return searchHaystack(product).includes(query)
  })

  return [...filtered].sort((a, b) => {
    if (sortBy.value === 'za') {
      return String(b.nome || '').localeCompare(String(a.nome || ''), 'pt')
    }
    if (sortBy.value === 'recent') return Number(b.id || 0) - Number(a.id || 0)
    return String(a.nome || '').localeCompare(String(b.nome || ''), 'pt')
  })
})

const hasActiveFilters = computed(() =>
  Boolean(
    localSearch.value.trim() ||
    Object.values(selectedFilters.value).some((value) => String(value ?? '').trim()),
  ),
)

async function fetchProducts({ resetCategory = false, silent = false } = {}) {
  const seq = ++fetchSeq
  const categorySlug = route.params.categorySlug

  if (!silent) {
    loading.value = true
    error.value = null
  }

  if (resetCategory) {
    categoryData.value = null
    modelCount.value = null
    unfilteredModels.value = null
    products.value = []
    resetPageControls()
  }

  try {
    if (!categorySlug) return

    await catalog.loadMeta()
    if (seq !== fetchSeq) return

    let category = categoryData.value
    if (resetCategory || !category) {
      // A lista de categorias já está em memória (cabeçalho/rodapé) — evita
      // uma ida ao servidor só para traduzir o slug em id.
      const rawCategory =
        knownCategories.value.find(
          (cat) => slugOfCategory(cat) === categorySlug && cat.tipo_catalogo,
        ) || (await catalog.fetchCategoryBySlug(categorySlug))
      if (seq !== fetchSeq) return

      category = { ...rawCategory, imagem: PLACEHOLDER }
      categoryData.value = category
      void resolveImageUrl(rawCategory.imagem, PLACEHOLDER).then((url) => {
        if (seq !== fetchSeq || categoryData.value?.id !== rawCategory.id) return
        if (url && url !== PLACEHOLDER) {
          categoryData.value = { ...categoryData.value, imagem: url }
        }
      })
      if (seq !== fetchSeq) return
      breadcrumbItems.value = [{ label: 'Início', to: { name: 'home' } }, { label: category.nome }]

      // Quiet initialization: every type filter starts visibly on "Todos".
      selectedFilters.value = blankFilters(
        catalog.filterDefinitionsForTipo(category.tipo_catalogo) || [],
      )
    }

    const tipo = category.tipo_catalogo
    if (!tipo) throw new ApiError('Categoria sem tipo de catálogo.', { status: 404 })

    const filters = Object.fromEntries(
      Object.entries(selectedFilters.value || {}).filter(([, value]) => String(value ?? '').trim()),
    )
    const models = await catalog.fetchCategoryModels(
      tipo,
      category.id,
      Object.keys(filters).length ? filters : null,
    )
    if (seq !== fetchSeq) return

    const visible = Array.isArray(models)
      ? models.filter((model) => {
          if (!model || model.visibilidade === false) return false
          const pt =
            model._storefront?.product_table ||
            catalog.storefrontContext(tipo, model)?.product_table
          if (!pt) return false
          const rows = Array.isArray(model[pt]) ? model[pt] : model[pt] ? [model[pt]] : []
          const hasEan = rows.some((p) => String(p?.ean || '').trim())
          const hasColor = (model.modelo_cores || []).some((c) => c && c.visibilidade !== false)
          return hasEan && hasColor
        })
      : []
    const prepared = visible.map((model) => {
      const cores = (model.modelo_cores || [])
        .filter((cor) => cor.visibilidade !== false)
        .sort((a, b) => a.numero - b.numero)
      return {
        model,
        coverPath: cores[0]?.imagem || '',
        galleryPaths: cores
          .slice(1)
          .map((cor) => cor.imagem)
          .filter(Boolean),
      }
    })

    const covers = await resolveImageUrls(
      prepared.map((entry) => entry.coverPath),
      PLACEHOLDER,
      { transform: IMG_CARD },
    )
    if (seq !== fetchSeq) return

    const nextProducts = prepared.map((entry, index) => ({
      ...entry.model,
      _tipo_catalogo: entry.model._tipo_catalogo || tipo,
      imagem_capa: covers[index] || PLACEHOLDER,
      galeria: [],
      _galleryPaths: entry.galleryPaths,
      currentImgIdx: 0,
    }))
    products.value = nextProducts
    if (!Object.keys(filters).length) {
      modelCount.value = nextProducts.length
      unfilteredModels.value = nextProducts
    }
    void hydrateGalleries(nextProducts, seq)
  } catch (err) {
    if (seq !== fetchSeq) return
    error.value = errorKind(err)
    console.error(err)
  } finally {
    if (seq === fetchSeq && !silent) loading.value = false
  }
}

async function hydrateGalleries(list, seq) {
  const pending = list.filter(
    (product) => (product._galleryPaths || []).length && !(product.galeria || []).length,
  )
  if (!pending.length) return

  const urls = await resolveImageUrls(
    pending.flatMap((product) => product._galleryPaths),
    PLACEHOLDER,
    { transform: IMG_CARD },
  )
  if (seq !== fetchSeq) return

  let offset = 0
  let changed = false
  for (const product of pending) {
    const count = product._galleryPaths.length
    const galeria = urls.slice(offset, offset + count).filter(Boolean)
    offset += count
    const live = products.value.find((row) => row.id === product.id)
    if (!live) continue
    live.galeria = galeria
    changed = true
  }
  // Garante re-render do SoftImage / setas após hydrate assíncrono
  if (changed) products.value = products.value.map((row) => ({ ...row }))
}

function galleryImages(product) {
  return [product.imagem_capa, ...(product.galeria || [])].filter(Boolean)
}

const hasGallery = (product) =>
  galleryImages(product).length > 1 || (product._galleryPaths || []).length > 0

const coverImage = (product) => {
  const images = galleryImages(product)
  if (!images.length) return PLACEHOLDER
  const idx = (((product.currentImgIdx || 0) % images.length) + images.length) % images.length
  return images[idx] || PLACEHOLDER
}

const prevImg = (e, product) => {
  e.preventDefault()
  e.stopPropagation()
  const live = products.value.find((row) => row.id === product.id) || product
  const imgs = galleryImages(live)
  if (imgs.length < 2) return
  live.currentImgIdx = ((live.currentImgIdx || 0) - 1 + imgs.length) % imgs.length
}

const nextImg = (e, product) => {
  e.preventDefault()
  e.stopPropagation()
  const live = products.value.find((row) => row.id === product.id) || product
  const imgs = galleryImages(live)
  if (imgs.length < 2) return
  live.currentImgIdx = ((live.currentImgIdx || 0) + 1) % imgs.length
}

watch(
  () => route.params.categorySlug,
  () => void fetchProducts({ resetCategory: true }),
)
onMounted(async () => {
  await fetchProducts({ resetCategory: true })
})
</script>

<template>
  <div class="products-page">
    <Breadcrumbs :items="breadcrumbItems" />

    <header class="category-head">
      <div class="head-inner">
        <div class="head-text">
          <h1>{{ pretty(categoryData?.nome) || 'Catálogo' }}</h1>
          <p v-if="categoryData && !loading" class="head-count">
            {{ products.length }} {{ products.length === 1 ? 'modelo' : 'modelos' }}
            <template v-if="hasActiveFilters"> · a mostrar {{ displayedProducts.length }}</template>
          </p>
          <p v-else class="head-count">&nbsp;</p>
          <p v-if="categoryData && products.length && !loading" class="head-print">
            <RouterLink
              :to="{ name: 'catalogue-print', query: { categoria: slugOfCategory(categoryData) } }"
            >
              Catálogo desta categoria para imprimir ou guardar em PDF
            </RouterLink>
          </p>
        </div>
        <div
          v-if="heroImageUrl && heroImageUrl !== PLACEHOLDER"
          class="head-media"
          aria-hidden="true"
        >
          <img
            :src="heroSrc"
            :srcset="heroSrcset"
            sizes="(max-width: 1000px) 32vw, 320px"
            alt=""
            width="320"
            height="180"
            loading="lazy"
            decoding="async"
          />
        </div>
      </div>
    </header>

    <!-- Sempre presente: aparecer só com os dados empurrava a grelha 93 px (CLS 0.15). -->
    <div class="toolbar">
      <div class="toolbar-inner">
        <label class="tool tool--search">
          <span class="tool-label">Pesquisar</span>
          <input
            v-model="localSearch"
            class="field-input"
            type="search"
            placeholder="Nome do modelo, cor ou EAN"
          />
        </label>
        <label class="tool">
          <span class="tool-label">Ordenar</span>
          <select v-model="sortBy" class="field-select">
            <option value="az">Nome (A–Z)</option>
            <option value="za">Nome (Z–A)</option>
            <option value="recent">Mais recentes</option>
          </select>
        </label>
        <label v-for="filterDef in visibleFilterDefs" :key="filterDef.field" class="tool">
          <span class="tool-label">{{ filterDef.label }}</span>
          <select
            class="field-select"
            :value="selectedFilters[filterDef.field] ?? ''"
            @change="onFilterChange(filterDef.field, $event.target.value)"
          >
            <option value="">Todos</option>
            <option v-for="opt in filterOptions(filterDef)" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </label>
      </div>
    </div>

    <div class="page-shell page-shell--grid">
      <div
        v-if="loading && !products.length"
        class="grid"
        aria-busy="true"
        aria-label="A carregar modelos"
      >
        <div v-for="n in 8" :key="n" class="card card--skeleton">
          <span class="card-media skeleton" />
          <span class="card-body"><span class="sk sk-title" /><span class="sk sk-sub" /></span>
        </div>
      </div>

      <ErrorState
        v-else-if="error"
        :kind="error"
        :title="error === 'not-found' ? 'Esta categoria já não está disponível' : ''"
        :text="
          error === 'not-found'
            ? 'Pode ter sido retirada do catálogo. Veja as outras categorias.'
            : ''
        "
        :back="
          error === 'not-found' ? { to: { name: 'categories' }, label: 'Ver o catálogo' } : null
        "
        @retry="fetchProducts({ resetCategory: true })"
      />

      <ul v-else-if="displayedProducts.length" class="grid">
        <li
          v-for="(product, i) in displayedProducts"
          :key="product.id"
          v-memo="[product.id, product.nome, coverImage(product), tipoLabel(product)]"
        >
          <RouterLink :to="modelDetailRoute(categoryData, product)" class="card">
            <span class="card-media">
              <SoftImage
                :src="coverImage(product)"
                alt=""
                :eager="i < 4"
                img-class="card-img"
                thumb
              />
              <span v-if="tipoLabel(product)" class="card-badge">{{ tipoLabel(product) }}</span>
            </span>
            <span class="card-body">
              <span class="card-name">{{ product.nome }}</span>
              <span class="card-meta">
                {{
                  (product.modelo_cores || []).length > 1
                    ? `${(product.modelo_cores || []).length} cores`
                    : 'Ver detalhes'
                }}
              </span>
            </span>
          </RouterLink>
          <span v-if="hasGallery(product)" class="card-nav">
            <button
              type="button"
              class="nav-btn"
              aria-label="Cor anterior"
              @click.prevent.stop="prevImg($event, product)"
            >
              <svg
                viewBox="0 0 24 24"
                width="18"
                height="18"
                fill="none"
                stroke="currentColor"
                stroke-width="2.2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
            <button
              type="button"
              class="nav-btn"
              aria-label="Cor seguinte"
              @click.prevent.stop="nextImg($event, product)"
            >
              <svg
                viewBox="0 0 24 24"
                width="18"
                height="18"
                fill="none"
                stroke="currentColor"
                stroke-width="2.2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="M9 18l6-6-6-6" />
              </svg>
            </button>
          </span>
        </li>
      </ul>

      <div v-else-if="categoryData" class="state empty">
        <div>
          <h2>
            {{
              hasActiveFilters
                ? 'Nenhum modelo corresponde aos filtros'
                : 'Ainda não há modelos nesta categoria'
            }}
          </h2>
          <p>
            {{
              hasActiveFilters
                ? 'Altere a pesquisa ou escolha «Todos» nos filtros.'
                : 'Estamos a preparar esta categoria. Veja as outras ou peça-nos um orçamento diretamente.'
            }}
          </p>
        </div>
        <button
          v-if="hasActiveFilters"
          type="button"
          class="btn btn-secondary"
          @click="clearFilters"
        >
          Limpar filtros
        </button>
        <RouterLink v-else to="/categorias" class="btn btn-secondary">Ver catálogo</RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ---------- Cabeçalho da categoria ---------- */
.category-head {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.head-inner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 2rem;
  max-width: calc(var(--content-max) + 2 * var(--page-pad));
  margin: 0 auto;
  padding: 2.25rem var(--page-pad);
}

.head-print {
  margin: 0.35rem 0 0;
  font-size: 0.92rem;
}

.head-print a {
  font-weight: 600;
}

.head-count {
  margin: 0.4rem 0 0;
  color: var(--color-muted);
  font-variant-numeric: tabular-nums;
}

.head-media {
  width: min(320px, 32vw);
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: var(--radius-lg);
  background: var(--color-bg-soft);
}

.head-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* ---------- Filtros ---------- */
.toolbar {
  position: sticky;
  top: var(--header-h);
  z-index: 50;
  background: var(--color-toolbar-bg);
  border-bottom: 1px solid var(--color-border);
  backdrop-filter: blur(6px);
}

.toolbar-inner {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.75rem 1rem;
  max-width: calc(var(--content-max) + 2 * var(--page-pad));
  margin: 0 auto;
  padding: 0.85rem var(--page-pad);
}

.tool {
  display: grid;
  gap: 0.3rem;
  flex: 0 1 200px;
}

.tool--search {
  flex: 1 1 280px;
}

.tool-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-muted);
}

.tool .field-input,
.tool .field-select {
  min-height: 40px;
  padding-top: 0.4rem;
  padding-bottom: 0.4rem;
  font-size: 0.95rem;
}

/* ---------- Grelha de modelos ---------- */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr));
  gap: 1.25rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.card {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  color: inherit;
  transition:
    border-color var(--transition),
    box-shadow var(--transition);
}

.card:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-md);
  color: inherit;
}

.card-media {
  position: relative;
  display: block;
  aspect-ratio: 1;
  overflow: hidden;
  background: var(--color-bg-soft);
}

.card-media :deep(.soft-image),
.card-media :deep(.soft-image__img) {
  width: 100%;
  height: 100%;
}

.card-media :deep(.soft-image__img) {
  object-fit: cover;
  transition:
    opacity 0.3s ease,
    transform 0.5s cubic-bezier(0.2, 0, 0, 1);
}

.card:hover .card-media :deep(.soft-image__img) {
  transform: scale(1.03);
}

.card-badge {
  position: absolute;
  left: 0.6rem;
  top: 0.6rem;
  padding: 0.2rem 0.55rem;
  border-radius: var(--radius-sm);
  background: var(--color-chip-bg);
  color: var(--color-ink);
  font-size: 0.75rem;
  font-weight: 600;
}

/* Irmão da ligação, não filho (HTML válido, A11Y-09): fica no canto da foto, que é quadrada. */
.grid > li {
  position: relative;
  container-type: inline-size;
}

.card-nav {
  position: absolute;
  top: calc(100cqw - 34px - 0.5rem - 1px);
  right: calc(0.5rem + 1px);
  display: flex;
  gap: 0.35rem;
  opacity: 0;
  transition: opacity var(--transition);
}

.grid > li:hover .card-nav,
.grid > li:focus-within .card-nav {
  opacity: 1;
}

@media (hover: none) {
  .card-nav {
    opacity: 1;
  }
}

.nav-btn {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 50%;
  background: var(--color-chip-bg);
  color: var(--color-ink);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
}

.nav-btn:hover {
  color: var(--color-accent);
}

.card-body {
  display: grid;
  gap: 0.2rem;
  padding: 0.85rem 1rem 1rem;
}

.card-name {
  color: var(--color-ink-deep);
  font-weight: 640;
  line-height: 1.3;
}

.card-meta {
  color: var(--color-muted);
  font-size: 0.875rem;
}

/* ---------- Estados ---------- */
.card--skeleton {
  pointer-events: none;
}

.sk-title {
  width: 70%;
}

.sk-sub {
  width: 35%;
  margin-top: 0.4rem;
}

.empty {
  padding: 2rem;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.empty h2 {
  margin-bottom: 0.35rem;
  font-size: 1.2rem;
}

.empty p {
  color: var(--color-muted);
}

@media (max-width: 720px) {
  .head-inner {
    grid-template-columns: minmax(0, 1fr);
    padding-top: 1.5rem;
    padding-bottom: 1.5rem;
  }

  .head-media {
    display: none;
  }

  .toolbar {
    position: static;
  }

  .tool {
    flex: 1 1 140px;
  }

  /* A pesquisa a toda a largura: com 164 px o texto de ajuda aparecia cortado (FE-18). */
  .tool--search {
    flex: 1 1 100%;
  }

  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
  }

  .card-body {
    padding: 0.65rem 0.75rem 0.8rem;
  }
}
</style>
