<script setup>
import { ref, onMounted, onUnmounted, computed, watch, watchEffect } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { resolveImageUrls, PLACEHOLDER } from '@/lib/images'
import SoftImage from '@/components/SoftImage.vue'
import { setNoindex, watchDynamicTitle } from '@/composables/usePageMeta'
import { useCart } from '@/composables/useCart'
import { modelQtyRules } from '@/lib/quantity'
import { useWhatsAppMessage } from '@/composables/useWhatsAppMessage'
import { MIN_ORCAMENTO_MSG, SITE_ORIGIN } from '@/lib/constants'
import { describeModel, modelMeta, pickerNoun, pretty, realDescription } from '@/lib/describe'
import { productWhatsAppMessage } from '@/lib/whatsappMessage'
import { cartItemFor } from '@/lib/cartItem'
import { boxNote } from '@/lib/quantity'
import { isSingleProductMode } from '@/lib/storefrontFormat'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import ErrorState from '@/components/ErrorState.vue'
import LoadingState from '@/components/LoadingState.vue'
import QtyInput from '@/components/QtyInput.vue'
import ModelSpecs from '@/components/ModelSpecs.vue'
import ImageLightbox from '@/components/ImageLightbox.vue'
import StorageNotice from '@/components/StorageNotice.vue'
import { useCatalog } from '@/composables/useCatalog'
import { ApiError } from '@/lib/api'
import { errorKind } from '@/lib/errors'
import { categoryProductsRoute, modelDetailRoute } from '@/lib/catalogRoutes'

const route = useRoute()
const router = useRouter()
const cart = useCart()
const catalog = useCatalog()

const model = ref(null)
const storefrontCtx = ref(null)
const pickerOptions = ref([])
const colors = ref([])
const selectedPicker = ref(null)
const selectedColor = ref(null)
const category = ref(null)
const loading = ref(true)
const failure = ref(null) // null, 'not-found' (o produto já não existe) ou 'unavailable' (o servidor não respondeu)
const activeImage = ref('')
const selectedQty = ref(6)
const addedMsg = ref('')
const lightboxOpen = ref(false)

const singleProductMode = computed(() => isSingleProductMode(storefrontCtx.value))
const qtyStep = computed(() => modelQtyRules(model.value, category.value).step)
const qtyMin = computed(() => modelQtyRules(model.value, category.value).min)
const badgeText = computed(() => catalog.badgeLabel(model.value, model.value?._tipo_catalogo))
// «Vendido em caixas de 12 un.» explica o «incrementos de 12» quando o passo é a caixa (RP-08).
const specExtras = computed(() => [
  {
    label: 'Quantidade mínima no pedido',
    display: `${qtyMin.value} un. (incrementos de ${qtyStep.value})`,
  },
  ...(boxNote(model.value?.embalagem, qtyStep.value)
    ? [{ label: 'Venda', display: boxNote(model.value.embalagem, qtyStep.value) }]
    : []),
])
const selectedProduct = computed(() =>
  catalog.activeProduct(model.value, storefrontCtx.value, selectedPicker.value),
)

const displayImage = computed(() => activeImage.value || selectedColor.value?.imagem || PLACEHOLDER)

const categoryName = computed(() => pretty(category.value?.nome))

// A descrição que o cliente escreveu; sem ela, a que se gera das especificações (nunca o «Sem descrição» dos dados antigos).
const description = computed(
  () => realDescription(model.value?.descricao) || describeModel(model.value),
)

// Título e descrição iguais aos que o pré-render escreve no HTML (lib/describe.js): o Google lê os mesmos depois do JavaScript.
watchDynamicTitle(
  () => [model.value?.nome, categoryName.value, activeImage.value],
  () => {
    if (!model.value?.nome) return null
    return {
      ...modelMeta(model.value, categoryName.value),
      image: displayImage.value,
      path: route.path, // sem a query (SEO-05)
    }
  },
)

const breadcrumbItems = computed(() => {
  const items = [{ label: 'Início', to: { name: 'home' } }]
  if (category.value) {
    items.push({
      label: category.value.nome,
      to: categoryProductsRoute(category.value),
    })
  }
  if (model.value) {
    items.push({ label: model.value.nome })
  }
  return items
})

// O código de barras vem da BD com o URL assinado que tinha quando foi gerado, já expirado (FE-10, SEO-07). Resolve-se
// uma só vez, em todas as linhas de produto e antes de montar as opções do selector, para a ficha e o selector lerem o
// mesmo URL em qualquer modo (único, variantes, assento). Antes só o ramo das variantes corrigia as opções, e a ficha lê
// as opções: nos artigos únicos a imagem aparecia partida.
async function resolveBarcodes(data, table) {
  const raw = data[table]
  const rows = Array.isArray(raw) ? raw : raw ? [raw] : []
  if (!rows.length) return
  const urls = await resolveImageUrls(
    rows.map((row) => row?.barcode_url || ''),
    '',
  )
  const fresh = rows.map((row, i) => ({ ...row, barcode_url: urls[i] || '' }))
  model.value[table] = Array.isArray(raw) ? fresh : fresh[0]
}

const fetchProduct = async () => {
  try {
    loading.value = true
    failure.value = null
    addedMsg.value = ''
    model.value = null
    pickerOptions.value = []
    colors.value = []
    storefrontCtx.value = null

    const legacyId = route.params.legacyModelId
    const categorySlug = route.params.categorySlug
    const modelSlug = route.params.modelSlug
    const tipoQuery = route.query.tipo || null

    const detailPromise = legacyId
      ? catalog.fetchModelDetail({ modelId: legacyId, tipo: tipoQuery })
      : catalog.fetchModelDetail({ categorySlug, modelSlug, tipo: tipoQuery })

    const [, modelData] = await Promise.all([catalog.loadMeta(), detailPromise])

    const tipo = modelData._tipo_catalogo || tipoQuery
    storefrontCtx.value = catalog.storefrontContext(tipo, modelData)
    model.value = modelData
    category.value = modelData.categories

    if (category.value && model.value) {
      const canonical = modelDetailRoute(category.value, model.value)
      const currentModelKey = String(
        route.params.modelSlug || route.params.legacyModelId || '',
      ).trim()
      const canonicalModelKey = String(canonical.params?.modelSlug || '').trim()
      if (
        legacyId ||
        (currentModelKey && canonicalModelKey && currentModelKey !== canonicalModelKey)
      ) {
        await router.replace({ ...canonical, query: route.query })
        return
      }
    }

    const rawColors = (modelData.modelo_cores || [])
      .filter((c) => c.visibilidade !== false)
      .sort((a, b) => a.numero - b.numero)
    const colorUrls = await resolveImageUrls(
      rawColors.map((c) => c.imagem),
      PLACEHOLDER,
    )
    colors.value = rawColors.map((c, i) => ({ ...c, imagem: colorUrls[i] || PLACEHOLDER }))

    if (colors.value.length === 0) {
      throw new ApiError('Não existem cores disponíveis para este modelo.', { status: 404 })
    }

    await resolveBarcodes(modelData, storefrontCtx.value.product_table)
    pickerOptions.value = catalog.buildPickerOptions(modelData, storefrontCtx.value)
    if (pickerOptions.value.length === 0) {
      const label = storefrontCtx.value?.picker?.label || 'variante'
      throw new ApiError(`Não existem ${label.toLowerCase()} disponíveis para este modelo.`, {
        status: 404,
      })
    }

    if (singleProductMode.value && !selectedProduct.value) {
      throw new ApiError('Este modelo ainda não tem EAN registado.', { status: 404 })
    }

    selectColor(colors.value[0])
    // ?ean= (QR da etiqueta): abre já na dimensão/variante desse produto; sem ele, ou se não existir, a primeira.
    const wantedEan = String(route.query.ean || '').trim()
    selectPicker(
      (wantedEan && pickerOptions.value.find((o) => (o.product?.ean || o.value?.ean) === wantedEan)) ||
        pickerOptions.value[0],
    )
    selectedQty.value = qtyMin.value
  } catch (err) {
    failure.value = errorKind(err)
    console.error(err)
  } finally {
    loading.value = false
  }
}

const selectColor = (color) => {
  selectedColor.value = color
  activeImage.value = color.imagem
}

const selectPicker = (option) => {
  selectedPicker.value = option
}

const addToCart = () => {
  if (!selectedColor.value || !selectedPicker.value) return

  const product = selectedProduct.value
  if (!product?.ean) return

  // A mesma linha que o pedido rápido junta (lib/cartItem.js).
  cart.addItem(
    cartItemFor({
      model: model.value,
      category: category.value,
      product,
      color: selectedColor.value,
      quantity: selectedQty.value,
      image: selectedColor.value.imagem,
    }),
  )

  // Fica até se sair da página (FE-07): antes sumia aos 2,8 s, e quem não olhava não sabia se tinha juntado.
  addedMsg.value = `${selectedQty.value} un. adicionadas ao pedido.`
}

const goToCart = () => router.push({ name: 'cart' })

// Saída de um produto que já não existe: a categoria do endereço, ou o catálogo se o endereço não a tem.
const backTo = computed(() =>
  route.params.categorySlug
    ? {
        to: { name: 'products', params: { categorySlug: route.params.categorySlug } },
        label: 'Ver outros modelos',
      }
    : { to: { name: 'categories' }, label: 'Ver o catálogo' },
)

// Um produto que já não existe não se indexa (RP-04).
watch(failure, (kind) => setNoindex(kind === 'not-found'))

// O botão do WhatsApp leva o modelo, a cor e a medida escolhidos, o EAN e o endereço (RP-13); ao sair da página volta ao texto geral.
const whatsapp = useWhatsAppMessage()
watchEffect(() => {
  const product = selectedProduct.value
  if (!model.value || !product?.ean) return whatsapp.clear()
  const picker = storefrontCtx.value?.picker
  whatsapp.set(
    productWhatsAppMessage({
      name: model.value.nome,
      category: categoryName.value,
      // Com uma só cor o nome é «Sortido»: não diz nada.
      colour:
        colors.value.length > 1
          ? selectedColor.value?.nome || `${selectedColor.value?.numero}`
          : '',
      measureNoun: picker ? pickerNoun(picker)[0] : '',
      measure: picker ? selectedPicker.value?.label : '',
      ean: product.ean,
      url: `${SITE_ORIGIN}${route.path}`,
    }),
  )
})
onUnmounted(whatsapp.clear)

onMounted(fetchProduct)
watch(() => route.fullPath, fetchProduct)
</script>

<template>
  <div class="product-detail">
    <Breadcrumbs :items="breadcrumbItems" />

    <LoadingState v-if="loading" message="A carregar detalhes…" />
    <div v-else-if="failure" class="page-shell">
      <ErrorState
        :kind="failure"
        :title="failure === 'not-found' ? 'Este produto já não está disponível' : ''"
        :text="
          failure === 'not-found'
            ? 'Pode ter sido retirado do catálogo. Veja os outros modelos.'
            : ''
        "
        :back="failure === 'not-found' ? backTo : null"
        @retry="fetchProduct"
      />
    </div>

    <article v-else-if="model && selectedColor && selectedPicker" class="detail-layout page-shell">
      <section class="gallery">
        <button
          type="button"
          class="main-image-wrap"
          aria-label="Ampliar imagem"
          @click="lightboxOpen = true"
        >
          <SoftImage
            :src="displayImage"
            :alt="`${model.nome} — cor selecionada`"
            img-class="main-img"
            eager
            fetchpriority="high"
            sizes="(max-width: 900px) 100vw, 50vw"
          />
          <span class="zoom-hint" aria-hidden="true">Ampliar</span>
        </button>

        <div v-if="colors.length > 1" class="color-picker">
          <p class="color-picker-label">
            Cor {{ selectedColor.numero }}
            <span v-if="selectedColor.nome"> — {{ selectedColor.nome }}</span>
          </p>
          <div class="color-thumbs">
            <button
              v-for="c in colors"
              :key="c.numero"
              type="button"
              class="color-thumb-btn"
              :class="{ active: selectedColor.numero === c.numero }"
              :aria-pressed="selectedColor.numero === c.numero"
              :aria-label="c.nome ? `Cor ${c.numero} — ${c.nome}` : `Cor ${c.numero}`"
              :title="c.nome || `Cor ${c.numero}`"
              @click="selectColor(c)"
            >
              <SoftImage :src="c.imagem || PLACEHOLDER" alt="" :thumb-width="160" thumb />
            </button>
          </div>
        </div>
      </section>

      <section class="buy-column">
        <header class="product-header">
          <RouterLink v-if="category" class="cat-link" :to="categoryProductsRoute(category)">
            {{ categoryName }}
          </RouterLink>
          <span v-if="badgeText" class="badge-pill badge-soft">{{ badgeText }}</span>
          <h1>{{ model.nome }}</h1>
          <p v-if="description" class="product-desc">{{ description }}</p>
          <p v-else class="product-desc">
            Selecione a cor{{
              storefrontCtx?.picker
                ? ` e a ${String(storefrontCtx.picker.label || 'variante').toLowerCase()}`
                : ''
            }}, indique a quantidade e adicione ao pedido de orçamento.
          </p>
        </header>

        <div v-if="storefrontCtx?.picker" class="block">
          <h2 class="block-title">{{ storefrontCtx.picker.label }}</h2>
          <div class="picker-grid">
            <button
              v-for="option in pickerOptions"
              :key="option.id"
              type="button"
              class="picker-chip"
              :class="{ 'is-active': selectedPicker?.id === option.id }"
              :aria-pressed="selectedPicker?.id === option.id"
              @click="selectPicker(option)"
            >
              {{ option.label }}
            </button>
          </div>
        </div>

        <ModelSpecs :model="model" :specs="storefrontCtx?.specs || []" :extras="specExtras" />

        <div class="buy-box">
          <h2 class="buy-title">Pedido de orçamento</h2>
          <p class="buy-note">{{ MIN_ORCAMENTO_MSG }}</p>

          <QtyInput v-model="selectedQty" class="qty-block" :step="qtyStep" :min="qtyMin" hint />

          <div class="cart-actions">
            <button type="button" class="btn btn-primary btn-block" @click="addToCart">
              Adicionar ao pedido
            </button>
            <button type="button" class="btn btn-secondary btn-block" @click="goToCart">
              Ver pedido
            </button>
          </div>

          <!-- A região existe sempre e só o texto muda: os leitores de ecrã só anunciam com fiabilidade regiões já presentes (ARIA22). -->
          <div role="status">
            <p v-if="addedMsg" class="added-msg">
              {{ addedMsg }} <RouterLink :to="{ name: 'cart' }">Ver pedido</RouterLink>
            </p>
          </div>
          <StorageNotice />

          <div v-if="selectedProduct?.ean" class="ref-box">
            <img
              v-if="selectedProduct?.barcode_url"
              :src="selectedProduct.barcode_url"
              alt="Código de barras EAN"
              class="barcode-img"
            />
            <p class="ean-line">EAN {{ selectedProduct.ean }}</p>
          </div>
        </div>

        <p class="help-line">
          Dúvidas sobre este modelo?
          <RouterLink to="/contacto">Fale connosco</RouterLink>
        </p>
      </section>
    </article>
    <ImageLightbox
      :open="lightboxOpen"
      :src="displayImage"
      :alt="model?.nome || 'Produto Diomika'"
      @close="lightboxOpen = false"
    />
  </div>
</template>

<style scoped>
.product-detail {
  padding-bottom: 3.5rem;
  background: var(--color-surface);
}

.detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(0, 0.88fr);
  gap: clamp(1.75rem, 4vw, 3.25rem);
  align-items: start;
  padding-top: 1.75rem;
}

.gallery {
  position: sticky;
  top: calc(var(--header-h) + 1rem);
}

.main-image-wrap {
  display: block;
  width: 100%;
  padding: 0;
  cursor: zoom-in;
  border: none;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-bg-soft);
  aspect-ratio: 1;
  appearance: none;
  position: relative;
}

.zoom-hint {
  position: absolute;
  right: 0.75rem;
  bottom: 0.75rem;
  z-index: 2;
  padding: 0.35rem 0.65rem;
  border-radius: 999px;
  background: rgba(22, 29, 33, 0.72);
  color: #fff;
  font-size: 0.72rem;
  font-weight: 650;
  letter-spacing: 0.02em;
  pointer-events: none;
}

.main-image-wrap :deep(.soft-image),
.main-image-wrap :deep(.soft-image__img) {
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.main-image-wrap :deep(.soft-image__img) {
  object-fit: cover;
}

.color-picker {
  margin-top: 1.1rem;
}

.color-picker-label {
  margin: 0 0 0.65rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-muted);
}

.color-thumbs {
  display: flex;
  flex-wrap: nowrap;
  gap: 0.5rem;
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 0.35rem;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
}

.color-thumb-btn {
  padding: 0;
  border: 2px solid transparent;
  border-radius: var(--radius-md);
  overflow: hidden;
  width: 68px;
  height: 68px;
  flex: 0 0 68px;
  cursor: pointer;
  background: none;
  transition:
    border-color var(--transition),
    transform var(--transition);
}

.color-thumb-btn:hover {
  transform: translateY(-2px);
}

.color-thumb-btn.active {
  border-color: var(--color-accent);
}

.color-thumb-btn :deep(.soft-image),
.color-thumb-btn :deep(.soft-image__img) {
  width: 100%;
  height: 100%;
}

.color-thumb-btn :deep(.soft-image__img) {
  object-fit: cover;
}

.buy-column {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.product-header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.45rem;
}

.cat-link {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-accent);
}

.cat-link:hover {
  color: var(--color-accent-hover);
}

.product-header h1 {
  margin: 0.15rem 0 0.25rem;
  font-size: clamp(1.95rem, 3.2vw, 2.65rem);
  color: var(--color-ink-deep);
}

.product-desc {
  margin: 0.35rem 0 0;
  color: var(--color-muted);
  line-height: 1.6;
  font-size: 1.02rem;
}

.block-title,
.buy-title {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  font-weight: 650;
  color: var(--color-ink-deep);
}

.buy-box {
  padding: 1.4rem 1.45rem;
  border-radius: var(--radius-lg);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
}

.buy-note {
  margin: 0 0 1.1rem;
  font-size: 0.9rem;
  color: var(--color-muted);
  line-height: 1.5;
}

.qty-block {
  margin-bottom: 1rem;
}

.cart-actions {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.added-msg {
  margin: 0.85rem 0 0;
  text-align: center;
  font-weight: 600;
  color: var(--color-success);
}

.ref-box {
  margin-top: 1.15rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.45rem;
}

.barcode-img {
  max-height: 72px;
  width: auto;
}

.ean-line {
  margin: 0;
  font-family: ui-monospace, monospace;
  font-size: 0.85rem;
  color: var(--color-muted);
}

.help-line {
  margin: 0;
  font-size: 0.92rem;
  color: var(--color-muted);
}

.help-line a {
  font-weight: 600;
}

@media (max-width: 900px) {
  .detail-layout {
    /* minmax(0, …): com 1fr a linha de cores alargava a coluna e havia scroll horizontal a 320 px. */
    grid-template-columns: minmax(0, 1fr);
  }

  .gallery {
    position: static;
  }

  .main-image-wrap {
    aspect-ratio: 4 / 3;
    max-width: 640px;
  }
}
</style>
