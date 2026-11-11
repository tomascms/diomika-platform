<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCatalog } from '@/composables/useCatalog'
import { useCategories } from '@/composables/useCategories'
import { categoryProductsRoute, modelDetailRoute } from '@/lib/catalogRoutes'
import { pretty } from '@/lib/describe'
import { matchCategories } from '@/lib/search'
import { collectEans } from '@/lib/storefrontFormat'
import { captureEvent } from '@/lib/posthog'
import { resolveImageUrls, PLACEHOLDER, IMG_CARD } from '@/lib/images'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import ErrorState from '@/components/ErrorState.vue'
import LoadingState from '@/components/LoadingState.vue'
import SoftImage from '@/components/SoftImage.vue'

const route = useRoute()
const router = useRouter()
const catalog = useCatalog()
const { categories, load: loadCategories } = useCategories()
const query = ref(String(route.query.q || ''))
const models = ref([])
const loading = ref(false)
const error = ref(false) // a pesquisa falhou (o servidor não respondeu)
const breadcrumbItems = [{ label: 'Início', to: { name: 'home' } }, { label: 'Pesquisar' }]

const normalizedQuery = computed(() => query.value.trim())
const results = computed(() => models.value)
// O que a região de estado anuncia quando os resultados mudam (A11Y-08); vazio enquanto pesquisa ou se falhou.
const statusText = computed(() => {
  if (loading.value || error.value || normalizedQuery.value.length < 2) return ''
  const n = results.value.length
  return n ? `${n} ${n === 1 ? 'resultado' : 'resultados'}` : 'Sem resultados'
})
// «almofda» encontra a categoria Almofada mesmo que a API não devolva nada: a lista de categorias já está em memória (FE-06).
const categoryHits = computed(() =>
  normalizedQuery.value.length >= 2 ? matchCategories(normalizedQuery.value, categories.value) : [],
)

onMounted(() => void loadCategories().catch(() => {}))

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
    error.value = false
    return
  }
  const seq = ++searchSeq
  loading.value = true
  error.value = false
  try {
    const hits = await catalog.searchCatalog(q, { limit: 60 })
    if (seq !== searchSeq) return
    const flat = Array.isArray(hits) ? hits : []
    // O que se procura e com quantos resultados (RP-10), só com consentimento: as pesquisas sem resultado dizem o que falta.
    captureEvent('search', { term: q.slice(0, 80), results: flat.length })
    const covers = await resolveImageUrls(
      flat.map(
        (entry) =>
          entry.cover_path ||
          (entry.model?.modelo_cores || []).find((c) => c.visibilidade !== false)?.imagem ||
          '',
      ),
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
    error.value = true
    models.value = []
    console.error(e)
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

// A primeira pesquisa (abrir a página com `?q=`, ou vir da caixa do cabeçalho) sai logo: com a espera de 280 ms a página
// mostrava «Sem resultados» antes de ter perguntado. Ao escrever, espera-se que a pessoa pare.
watch(
  normalizedQuery,
  (q, previous) => {
    clearTimeout(searchTimer)
    if (previous === undefined) void runSearch(q)
    else searchTimer = setTimeout(() => runSearch(q), 280)
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
        <p>Pesquise por categoria, nome do modelo, cor, medida ou EAN.</p>
        <form class="search-form" role="search" @submit.prevent="submitSearch">
          <label class="visually-hidden" for="catalog-search">Pesquisar catálogo</label>
          <input
            id="catalog-search"
            v-model="query"
            class="field-input"
            type="search"
            placeholder="Ex.: almofada, 45x45, 5606044…"
            autofocus
          />
          <button class="btn btn-primary" type="submit">Pesquisar</button>
        </form>
      </header>
      <section
        v-if="categoryHits.length"
        class="category-hits"
        aria-labelledby="category-hits-title"
      >
        <h2 id="category-hits-title" class="category-hits__title">Categorias</h2>
        <ul class="category-hits__list">
          <li v-for="category in categoryHits" :key="category.id">
            <RouterLink :to="categoryProductsRoute(category)" class="category-hit">
              <strong>{{ pretty(category.nome) }}</strong>
              <span>Ver todos os modelos</span>
            </RouterLink>
          </li>
        </ul>
      </section>
      <!-- Sempre presente, só o texto muda: só assim os leitores de ecrã anunciam (ARIA22). -->
      <p class="visually-hidden" role="status">{{ statusText }}</p>
      <LoadingState v-if="loading" message="A pesquisar…" />
      <ErrorState v-else-if="error" @retry="runSearch(normalizedQuery)" />
      <div v-else-if="normalizedQuery.length >= 2 && results.length" class="result-grid">
        <RouterLink
          v-for="entry in results"
          :key="`${entry.category?.id}-${entry.model?.id}`"
          :to="modelDetailRoute(entry.category, entry.model)"
          class="result-card surface-card surface-card--elevated"
        >
          <div class="result-image">
            <SoftImage :src="entry.image" :alt="entry.model?.nome" thumb />
          </div>
          <div class="result-body">
            <span>{{ entry.category?.nome }}</span>
            <h2>{{ entry.model?.nome }}</h2>
            <small v-if="collectEans(entry.model).length"
              >EAN {{ collectEans(entry.model).slice(0, 2).join(', ') }}</small
            >
          </div>
        </RouterLink>
      </div>
      <div v-else-if="normalizedQuery.length >= 2" class="empty-state-block surface-card">
        <h2>Sem resultados</h2>
        <p>Experimente outra palavra: a categoria, o nome do modelo, a cor, a medida ou o EAN.</p>
      </div>
      <p v-else class="search-prompt">Introduza pelo menos 2 caracteres para pesquisar.</p>
    </div>
  </div>
</template>
<style scoped>
.search-page {
  min-height: 65vh;
  background: var(--color-surface);
  padding-bottom: 3rem;
}
.search-shell {
  padding-top: 2rem;
}
.search-header {
  max-width: 720px;
  margin-bottom: 2rem;
}
.search-header p,
.search-prompt {
  color: var(--color-muted);
}
.search-form {
  display: flex;
  gap: 0.65rem;
  margin-top: 1rem;
}
.search-form .field-input {
  flex: 1;
}
.category-hits {
  margin-bottom: 1.75rem;
}
.category-hits__title {
  margin: 0 0 0.6rem;
  font-size: 1rem;
  color: var(--color-muted);
}
.category-hits__list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.category-hit {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 11rem;
  padding: 0.8rem 1.1rem;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: inherit;
  text-decoration: none;
}
.category-hit:hover {
  border-color: var(--color-accent);
}
.category-hit strong {
  color: var(--color-ink-deep);
}
.category-hit span {
  color: var(--color-accent);
  font-size: 0.875rem;
  font-weight: 600;
}
.result-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0.85rem;
}
.result-card {
  overflow: hidden;
  color: inherit;
  text-decoration: none;
}
.result-image {
  aspect-ratio: 1;
  background: var(--color-bg-soft);
}
.result-image :deep(.soft-image__img) {
  object-fit: cover;
}
.result-body {
  padding: 1rem;
}
.result-body span,
.result-body small {
  color: var(--color-muted);
  font-size: 0.8rem;
}
.result-body h2 {
  margin: 0.3rem 0;
  font-size: 1.05rem;
}
.empty-state-block {
  max-width: 520px;
  padding: 2rem;
  text-align: center;
}
@media (max-width: 1400px) {
  .result-grid {
    grid-template-columns: repeat(5, 1fr);
  }
}
@media (max-width: 1100px) {
  .result-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
@media (max-width: 900px) {
  .result-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 560px) {
  .search-form {
    flex-direction: column;
  }
  .result-grid {
    grid-template-columns: 1fr;
  }
}
</style>
