<script setup>
// Catálogo para imprimir ou guardar em PDF (RP-14): o dono não tinha um catálogo para mandar por WhatsApp ou email.
// É uma página só com texto (sem fotografias, sem preços) e CSS de impressão; «Imprimir / guardar em PDF» abre o diálogo
// do navegador, que também guarda em PDF. Sem biblioteca de PDF e sem gerar nada no servidor: sai dos mesmos dados
// que o catálogo. `?categoria=<slug>` imprime só uma categoria.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import CompanyIdentity from '@/components/CompanyIdentity.vue'
import ErrorState from '@/components/ErrorState.vue'
import LoadingState from '@/components/LoadingState.vue'
import { useCatalog } from '@/composables/useCatalog'
import { useCategories } from '@/composables/useCategories'
import { categoryProductsRoute, categorySlug } from '@/lib/catalogRoutes'
import { MIN_ORDER } from '@/lib/constants'
import { pretty, realDescription, storeLabel } from '@/lib/describe'
import { errorKind } from '@/lib/errors'
import { ean13Drawing } from '@/lib/ean13Svg'
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
// Formato «nome(número)», por exemplo «Azul Ciano(12)».
const colorLabel = (c) => (c.nome ? `${c.nome}(${c.numero})` : `${c.numero}`)
const colorsText = (model) => {
  const list = colors(model)
  return `${list.length === 1 ? 'Cor' : 'Cores'}: ${list.map(colorLabel).join(', ')}`
}
// Fotos do próprio modelo (das suas cores), sem repetir, no máximo 5.
const PHOTOS_PER_MODEL = 5
// No papel: 3 modelos por página (cada página é de uma só categoria).
const PER_PAGE = 3
const chunk = (list, size) => {
  const out = []
  for (let i = 0; i < list.length; i += size) out.push(list.slice(i, i + size))
  return out
}
const photos = (model) => {
  const out = []
  for (const color of colors(model)) {
    for (const url of color.imagens?.length ? color.imagens : [color.imagem]) {
      if (url && !out.includes(url)) out.push(url)
    }
  }
  return out.slice(0, PHOTOS_PER_MODEL)
}
// Código de barras em vetor (nítido), desenhado pelo template: só para EAN válidos, senão nada.
const drawing = (ean) => ean13Drawing(ean)
const hasMeasure = (model) => variantList(model).some((variant) => variant.measure)

// No site é uma página normal. Só ao imprimir (ou guardar em PDF) os modelos passam a folhas A4 com 3 espaços iguais:
// `beforeprint` liga o modo papel (classe `is-paper`, medidas em mm iguais às do @page) e o que não cabe no seu espaço
// encolhe (CSS `zoom`, que volta a paginar o texto) até caber — procura-se o maior zoom que cabe. `afterprint` repõe o site.
const sheets = ref(null)
const MIN_ZOOM = 0.35
function fitModels() {
  for (const box of sheets.value?.querySelectorAll('.print-model') || []) {
    const body = box.querySelector('.print-fit')
    const style = getComputedStyle(box)
    const room = box.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom)
    const fits = () => body.getBoundingClientRect().height <= room
    body.style.zoom = ''
    if (fits()) continue
    let lo = MIN_ZOOM
    let hi = 1
    for (let i = 0; i < 8; i += 1) {
      const mid = (lo + hi) / 2
      body.style.zoom = String(mid)
      if (fits()) lo = mid
      else hi = mid
    }
    body.style.zoom = String(lo)
  }
}
function toPaper() {
  sheets.value?.classList.add('is-paper')
  fitModels()
}
function toScreen() {
  sheets.value?.classList.remove('is-paper')
  for (const body of sheets.value?.querySelectorAll('.print-fit') || []) body.style.zoom = ''
}

const printPage = () => window.print()

onMounted(() => {
  window.addEventListener('beforeprint', toPaper)
  window.addEventListener('afterprint', toScreen)
  build()
})
onBeforeUnmount(() => {
  window.removeEventListener('beforeprint', toPaper)
  window.removeEventListener('afterprint', toScreen)
})
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

      <div v-else ref="sheets" class="print-sheets">
        <section v-for="{ category, models } in sections" :key="category.id" class="print-category">
          <template v-for="(group, gi) in chunk(models, PER_PAGE)" :key="gi">
          <div class="print-page" :class="{ 'has-head': gi === 0 }">
          <div v-if="gi === 0" class="print-category-head">
            <h2>{{ pretty(category.nome) }}</h2>
            <RouterLink :to="categoryProductsRoute(category)" class="no-print print-category-link"
              >ver no site</RouterLink
            >
          </div>
          <article v-for="model in group" :key="model.id" class="print-model">
            <div class="print-fit">
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
            <div v-if="photos(model).length" class="print-photos">
              <img v-for="(url, i) in photos(model)" :key="`${url}-${i}`" :src="url" alt="" loading="eager" />
            </div>
            <p class="print-colors">{{ colorsText(model) }}</p>
            <div class="print-barcodes">
              <div v-for="variant in variantList(model)" :key="`bc-${variant.ean}`" class="print-barcode">
                <span v-if="hasMeasure(model)" class="print-barcode-measure">{{ variant.measure }}</span>
                <svg
                  v-if="drawing(variant.ean)"
                  class="print-barcode-svg"
                  :viewBox="drawing(variant.ean).viewBox"
                  role="img"
                  :aria-label="`EAN ${drawing(variant.ean).ean}`"
                >
                  <g fill="#000">
                    <rect
                      v-for="(bar, i) in drawing(variant.ean).bars"
                      :key="i"
                      :x="bar.x"
                      y="0"
                      :width="bar.width"
                      :height="bar.height"
                    />
                  </g>
                  <g font-family="Arial, Helvetica, sans-serif" font-size="9" fill="#000">
                    <text
                      v-for="(t, i) in drawing(variant.ean).texts"
                      :key="i"
                      :x="t.x"
                      :y="drawing(variant.ean).baseline"
                      text-anchor="middle"
                    >{{ t.text }}</text>
                  </g>
                </svg>
              </div>
            </div>
            </div>
          </article>
          </div>
          </template>
        </section>
      </div>
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
  margin-top: 2.5rem;
}

/* No site cada folha desaparece (os modelos ficam seguidos por categoria). */
.print-page {
  display: contents;
}

.print-fit {
  width: 100%;
}

/* Modo papel (ligado só ao imprimir): folhas A4 com 14 mm de margem, 182 × 267 mm, 3 espaços iguais. */
.is-paper .print-page {
  box-sizing: border-box;
  display: grid;
  width: 182mm;
  height: 267mm;
  grid-template-rows: repeat(3, minmax(0, 1fr));
  gap: 3mm;
  overflow: hidden;
  break-before: page;
}

/* A primeira folha de cada categoria leva o nome por cima dos 3 espaços. */
.is-paper .print-page.has-head {
  grid-template-rows: auto repeat(3, minmax(0, 1fr));
}

.is-paper .print-model {
  min-height: 0;
  overflow: hidden;
  margin: 0;
  padding: 3mm 3.5mm;
  border-color: #999;
  box-shadow: none;
  break-inside: avoid;
}

.is-paper .print-category {
  margin-top: 0;
}

.is-paper .print-photos {
  grid-template-columns: repeat(5, 1fr);
  max-width: none;
}

.is-paper .print-barcode {
  flex: 0 0 120px;
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
  margin-top: 1rem;
  padding: 1.1rem 1.25rem;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.print-model h3 {
  margin: 0;
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

/* As fotos ocupam a largura toda: exatamente 5 colunas iguais, quadradas (a proporção não muda). */
.print-photos {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.5rem;
  max-width: 680px;
  margin: 0.6rem 0 0;
}

.print-photos img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border: 1px solid var(--color-border);
}

/* Códigos de barras: 9 em linha que ocupam toda a largura (cada um 1/9), por baixo das cores. */
.print-barcodes {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 1.5mm 1mm;
  margin-top: 0.6rem;
}

.print-barcode {
  flex: 0 0 calc((100% - 8mm) / 9);
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  break-inside: avoid;
}

.print-barcode-measure {
  width: 100%;
  overflow: hidden;
  text-align: center;
  font-size: 0.68rem;
  white-space: nowrap;
  text-overflow: clip;
}

.print-barcode-svg {
  display: block;
  width: 100%;
  height: auto;
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

  /* Só os produtos saem no papel: sem título, texto nem identificação da empresa. Tudo seguido, sem quebras entre categorias. */
  .print-catalogue .print-head {
    display: none !important;
  }

  /* Nada depois da última folha: um espaço a mais dava uma página em branco no fim do PDF. */
  .print-catalogue,
  .app-main {
    padding-bottom: 0 !important;
    margin-bottom: 0 !important;
  }

  .print-catalogue a {
    color: inherit;
    text-decoration: none;
  }
}
</style>
