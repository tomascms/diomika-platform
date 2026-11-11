<script setup>
// Catálogo para imprimir ou guardar em PDF (RP-14): o dono não tinha um catálogo para mandar por WhatsApp ou email.
// É uma página só com texto (sem fotografias, sem preços) e CSS de impressão; «Imprimir / guardar em PDF» abre o diálogo
// do navegador, que também guarda em PDF. Sem biblioteca de PDF e sem gerar nada no servidor: sai dos mesmos dados
// que o catálogo. `?categoria=<slug>` imprime só uma categoria.
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import CompanyIdentity from '@/components/CompanyIdentity.vue'
import ErrorState from '@/components/ErrorState.vue'
import LoadingState from '@/components/LoadingState.vue'
import { useCatalog } from '@/composables/useCatalog'
import { useCategories } from '@/composables/useCategories'
import { categoryProductsRoute, categorySlug } from '@/lib/catalogRoutes'
import { MIN_ORDER } from '@/lib/constants'
import { pickerNoun, pretty, realDescription, storeLabel } from '@/lib/describe'
import { errorKind } from '@/lib/errors'
import { showableModel, specRows, variantList } from '@/lib/storefrontFormat'

const route = useRoute()
const catalog = useCatalog()
const { categories, load } = useCategories()

const sections = ref([]) // [{ category, models }] só com modelos mostráveis
const loading = ref(true)
const failure = ref(null)
const today = new Date().toLocaleDateString('pt-PT', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
})

const wanted = computed(() => String(route.query.categoria || '').trim())
const only = computed(() => (wanted.value ? sections.value[0]?.category : null))
const heading = computed(() =>
  only.value ? `Catálogo Diomika — ${pretty(only.value.nome)}` : 'Catálogo Diomika',
)
const breadcrumbItems = computed(() => [
  { label: 'Início', to: { name: 'home' } },
  { label: 'Catálogo', to: { name: 'categories' } },
  { label: 'Para imprimir' },
])

const nonEmpty = (list) => list.filter((entry) => entry.models.length)

/** Lê as categorias, três de cada vez (a lista de cada uma vem da API, e da cache da loja quando já foi vista). */
async function loadSections(chosen) {
  const out = []
  const pending = chosen.map((category, index) => ({ category, index }))
  const worker = async () => {
    while (pending.length) {
      const { category, index } = pending.shift()
      const models = await catalog.fetchCategoryModels(category.tipo_catalogo, category.id)
      out[index] = { category, models: (Array.isArray(models) ? models : []).filter(showableModel) }
    }
  }
  await Promise.all(Array.from({ length: Math.min(3, pending.length) }, worker))
  return nonEmpty(out)
}

async function build() {
  loading.value = true
  failure.value = null
  try {
    await Promise.all([load(), catalog.loadMeta()])
    const chosen = categories.value.filter(
      (category) =>
        category.tipo_catalogo && (!wanted.value || categorySlug(category) === wanted.value),
    )
    sections.value = await loadSections(chosen)
  } catch (err) {
    failure.value = errorKind(err)
    console.error(err)
  } finally {
    loading.value = false
  }
}

// No papel não se repete o que a tabela já diz: só a descrição escrita pelo cliente, as especificações que não são as
// medidas (a tabela tem-nas, com o EAN) e as cores.
const specs = (model) =>
  specRows(model, model._storefront?.specs).filter((row) => row.widget !== 'dimension_list')
const colors = (model) =>
  (model.modelo_cores || [])
    .filter((c) => c && c.visibilidade !== false)
    .sort((a, b) => a.numero - b.numero)
const colorsText = (model) => {
  const list = colors(model)
  if (list.length === 1)
    return `Cor: ${list[0].nome || `n.º ${list[0].numero}`}${list[0].nome ? ` (n.º ${list[0].numero})` : ''}`
  return `Cores: ${list.map((c) => [c.numero, c.nome].filter(Boolean).join(' ')).join(', ')}`
}
const measureHeading = (model) => pretty(pickerNoun(model._storefront?.picker)[0])
const hasMeasure = (model) => variantList(model).some((variant) => variant.measure)

const printPage = () => window.print()

onMounted(build)
</script>

<template>
  <div class="print-catalogue">
    <Breadcrumbs :items="breadcrumbItems" />
    <div class="page-shell">
      <header class="print-head">
        <h1 class="page-title">{{ heading }}</h1>
        <p class="print-lead">
          Modelos, medidas, cores e EAN. Sem preços: peça orçamento. Pedido mínimo de
          {{ MIN_ORDER }}.
          <span class="print-date">Gerado em {{ today }}.</span>
        </p>
        <CompanyIdentity class="print-company" />
      </header>

      <div class="print-toolbar no-print">
        <button
          type="button"
          class="btn btn-primary"
          :disabled="loading || !sections.length"
          @click="printPage"
        >
          Imprimir / guardar em PDF
        </button>
        <RouterLink v-if="wanted" :to="{ name: 'catalogue-print' }" class="btn btn-secondary"
          >Catálogo completo</RouterLink
        >
        <RouterLink to="/pedido-rapido" class="btn btn-secondary">Pedido rápido por EAN</RouterLink>
      </div>

      <LoadingState v-if="loading" message="A preparar o catálogo…" />
      <ErrorState v-else-if="failure" :kind="failure" @retry="build" />
      <div v-else-if="!sections.length" class="surface-card print-empty">
        <p>Não há modelos para imprimir{{ wanted ? ' nesta categoria' : '' }}.</p>
        <RouterLink :to="{ name: 'categories' }" class="btn btn-secondary"
          >Ver o catálogo</RouterLink
        >
      </div>

      <template v-else>
        <section v-for="{ category, models } in sections" :key="category.id" class="print-category">
          <div class="print-category-head">
            <h2>{{ pretty(category.nome) }}</h2>
            <RouterLink :to="categoryProductsRoute(category)" class="no-print print-category-link"
              >ver no site</RouterLink
            >
          </div>
          <article v-for="model in models" :key="model.id" class="print-model">
            <h3>{{ model.nome }}</h3>
            <p v-if="realDescription(model.descricao)" class="print-desc">
              {{ realDescription(model.descricao) }}
            </p>
            <dl v-if="specs(model).length" class="print-specs">
              <template v-for="row in specs(model)" :key="row.field">
                <dt>{{ storeLabel(row.label) }}</dt>
                <dd>{{ row.display }}</dd>
              </template>
            </dl>
            <table class="print-table">
              <thead>
                <tr>
                  <th v-if="hasMeasure(model)" scope="col">{{ measureHeading(model) }}</th>
                  <th scope="col">EAN</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="variant in variantList(model)" :key="variant.ean">
                  <td v-if="hasMeasure(model)">{{ variant.measure }}</td>
                  <td class="print-ean">{{ variant.ean }}</td>
                </tr>
              </tbody>
            </table>
            <p class="print-colors">{{ colorsText(model) }}</p>
          </article>
        </section>
      </template>
    </div>
  </div>
</template>

<style scoped>
.print-catalogue {
  background: var(--color-surface);
  padding-bottom: 2rem;
}

.print-head {
  margin-bottom: 1.25rem;
}

.print-lead {
  max-width: 70ch;
  margin: 0 0 1rem;
  color: var(--color-muted);
}

.print-date {
  white-space: nowrap;
}

.print-company {
  font-size: 0.92rem;
  color: var(--color-ink-soft);
}

.print-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  margin-bottom: 1.5rem;
}

.print-empty {
  max-width: 520px;
  padding: 2rem;
  text-align: center;
}

.print-category {
  margin-top: 2rem;
}

.print-category-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.25rem 0.75rem;
  padding-bottom: 0.4rem;
  border-bottom: 2px solid var(--color-ink-deep);
}

.print-category-link {
  font-size: 0.9rem;
  font-weight: 600;
}

.print-model {
  margin-top: 1.25rem;
  padding: 1rem 1.15rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.print-desc {
  margin: 0.35rem 0 0.6rem;
  color: var(--color-ink-soft);
}

.print-specs {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.15rem 1rem;
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
}

.print-specs dt {
  color: var(--color-muted);
}

.print-specs dd {
  margin: 0;
}

.print-table {
  border-collapse: collapse;
  font-size: 0.95rem;
}

.print-table th,
.print-table td {
  padding: 0.25rem 1.25rem 0.25rem 0;
  border-bottom: 1px solid var(--color-border);
  text-align: left;
}

.print-ean {
  font-family: var(--font-mono);
  letter-spacing: 0.02em;
}

.print-colors {
  margin: 0.6rem 0 0;
  font-size: 0.92rem;
  color: var(--color-ink-soft);
}
</style>

<style>
/* Só o conteúdo do catálogo sai no papel: sem cabeçalho, rodapé, WhatsApp, banner de cookies nem botões. */
@media print {
  @page {
    size: A4;
    margin: 14mm;
  }

  .app-header,
  .app-footer,
  .whatsapp-fab,
  .cookie-banner,
  .skip-link,
  .print-catalogue .breadcrumbs,
  .print-catalogue .no-print {
    display: none !important;
  }

  .app-container,
  .app-main,
  .print-catalogue {
    min-height: 0 !important;
    background: #fff !important;
  }

  .print-catalogue .page-shell {
    max-width: none;
    padding: 0;
  }

  .print-catalogue .print-category {
    break-before: page;
  }

  .print-catalogue .print-category:first-of-type {
    break-before: auto;
  }

  .print-catalogue .print-model {
    break-inside: avoid;
    border-color: #999;
  }

  .print-catalogue a {
    color: inherit;
    text-decoration: none;
  }
}
</style>
