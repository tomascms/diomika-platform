<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCatalog } from '@/composables/useCatalog'
import { modelDetailRoute } from '@/lib/catalogRoutes'
import { resolveImageUrls, PLACEHOLDER, IMG_CARD } from '@/lib/images'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import LoadingState from '@/components/LoadingState.vue'
import SoftImage from '@/components/SoftImage.vue'

const route = useRoute()
const router = useRouter()
const catalog = useCatalog()
const query = ref(String(route.query.q || ''))
const models = ref([])
const loading = ref(false)
const error = ref('')
const breadcrumbItems = [{ label: 'Início', to: { name: 'home' } }, { label: 'Pesquisar' }]

function eansIn(value, found = []) {
  if (!value || typeof value !== 'object') return found
  if (Array.isArray(value)) { value.forEach((entry) => eansIn(entry, found)); return found }
  for (const [key, entry] of Object.entries(value)) {
    if (key === 'ean' && entry != null) found.push(String(entry))
    else if (entry && typeof entry === 'object') eansIn(entry, found)
  }
  return found
}

const normalizedQuery = computed(() => query.value.trim())
const results = computed(() => models.value)

function submitSearch() {
  router.replace({ name: 'search', query: query.value.trim() ? { q: query.value.trim() } : {} })
}

let searchSeq = 0
let searchTimer = null

async function runSearch(term) {
  const q = term.trim()
  if (q.length < 2) {
    models.value = []
    loading.value = false
    error.value = ''
    return
  }
  const seq = ++searchSeq
  loading.value = true
  error.value = ''
  try {
    const hits = await catalog.searchCatalog(q, { limit: 60 })
    if (seq !== searchSeq) return
    const flat = Array.isArray(hits) ? hits : []
    const covers = await resolveImageUrls(
      flat.map((entry) => entry.cover_path || (entry.model?.modelo_cores || []).find((c) => c.visibilidade !== false)?.imagem || ''),
      PLACEHOLDER,
      { transform: IMG_CARD },
    )
    if (seq !== searchSeq) return
    models.value = flat.map((entry, index) => ({
      model: entry.model,
      category: entry.category,
      image: covers[index] || PLACEHOLDER,
    }))
  } catch (e) {
    if (seq !== searchSeq) return
    error.value = e.message || 'Não foi possível pesquisar o catálogo.'
    models.value = []
  } finally {
    if (seq === searchSeq) loading.value = false
  }
}

watch(
  () => route.query.q,
  (q) => {
    query.value = String(q || '')
  },
)

watch(
  normalizedQuery,
  (q) => {
    clearTimeout(searchTimer)
    searchTimer = setTimeout(() => runSearch(q), 280)
  },
  { immediate: true },
)
</script>
<template>
  <div class="search-page">
    <Breadcrumbs :items="breadcrumbItems" />
    <div class="page-shell search-shell">
      <header class="search-header">
        <h1 class="page-title">Pesquisar catálogo</h1>
        <p>Pesquise pelo nome do modelo, referência ou EAN.</p>
        <form class="search-form" role="search" @submit.prevent="submitSearch">
          <label class="sr-only" for="catalog-search">Pesquisar catálogo</label>
          <input id="catalog-search" v-model="query" class="field-input" type="search" placeholder="Ex.: modelo, slug ou EAN" autofocus />
          <button class="btn btn-primary" type="submit">Pesquisar</button>
        </form>
      </header>
      <LoadingState v-if="loading" message="A pesquisar…" />
      <p v-else-if="error" class="alert alert-error">{{ error }}</p>
      <div v-else-if="normalizedQuery.length >= 2 && results.length" class="result-grid">
        <RouterLink v-for="entry in results" :key="`${entry.category?.id}-${entry.model?.id}`" :to="modelDetailRoute(entry.category, entry.model)" class="result-card surface-card surface-card--elevated">
          <div class="result-image"><SoftImage :src="entry.image" :alt="entry.model?.nome" thumb /></div>
          <div class="result-body"><span>{{ entry.category?.nome }}</span><h2>{{ entry.model?.nome }}</h2><small v-if="eansIn(entry.model).length">EAN {{ eansIn(entry.model).slice(0, 2).join(', ') }}</small></div>
        </RouterLink>
      </div>
      <div v-else-if="normalizedQuery.length >= 2" class="empty-state-block surface-card"><h2>Sem resultados</h2><p>Experimente outro nome, referência ou EAN.</p></div>
      <p v-else class="search-prompt">Introduza pelo menos 2 caracteres para pesquisar.</p>
    </div>
  </div>
</template>
<style scoped>
.search-page { min-height: 65vh; background: #fff; padding-bottom: 3rem; }
.search-shell { padding-top: 2rem; }
.search-header { max-width: 720px; margin-bottom: 2rem; }
.search-header p, .search-prompt { color: var(--color-muted); }
.search-form { display: flex; gap: 0.65rem; margin-top: 1rem; }
.search-form .field-input { flex: 1; }
.result-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 0.85rem; }
.result-card { overflow: hidden; color: inherit; text-decoration: none; }
.result-image { aspect-ratio: 1; background: var(--color-bg-soft); }
.result-image :deep(.soft-image__img) { object-fit: cover; }
.result-body { padding: 1rem; }
.result-body span, .result-body small { color: var(--color-muted); font-size: 0.8rem; }
.result-body h2 { margin: 0.3rem 0; font-size: 1.05rem; }
.empty-state-block { max-width: 520px; padding: 2rem; text-align: center; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); }
@media (max-width: 1400px) { .result-grid { grid-template-columns: repeat(5, 1fr); } }
@media (max-width: 1100px) { .result-grid { grid-template-columns: repeat(4, 1fr); } }
@media (max-width: 900px) { .result-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 560px) { .search-form { flex-direction: column; } .result-grid { grid-template-columns: 1fr; } }
</style>
