<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { resolveImageUrls, PLACEHOLDER } from '@/lib/images'
import SoftImage from '@/components/SoftImage.vue'
import { watchDynamicTitle } from '@/composables/usePageMeta'
import { useCart, resolveCartQtyRules } from '@/composables/useCart'
import { MIN_ORCAMENTO_MSG } from '@/lib/constants'
import { isSingleProductMode } from '@/lib/storefrontFormat'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import LoadingState from '@/components/LoadingState.vue'
import QtySelect from '@/components/QtySelect.vue'
import ModelSpecs from '@/components/ModelSpecs.vue'
import ImageLightbox from '@/components/ImageLightbox.vue'
import { useCatalog } from '@/composables/useCatalog'
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
const error = ref(null)
const activeImage = ref('')
const selectedQty = ref(6)
const addedMsg = ref('')
const lightboxOpen = ref(false)

const singleProductMode = computed(() => isSingleProductMode(storefrontCtx.value))
const qtyStep = computed(() => resolveCartQtyRules(category.value).step)
const qtyMin = computed(() => resolveCartQtyRules(category.value).min)
const badgeText = computed(() => catalog.badgeLabel(model.value, model.value?._tipo_catalogo))
const specExtras = computed(() => [
  { label: 'Quantidade mínima no pedido', display: `${qtyMin.value} un. (incrementos de ${qtyStep.value})` },
])
const selectedProduct = computed(() =>
  catalog.activeProduct(model.value, storefrontCtx.value, selectedPicker.value),
)

const displayImage = computed(
  () => activeImage.value || selectedColor.value?.imagem || PLACEHOLDER,
)

const categoryName = computed(() => {
  const t = String(category.value?.nome || '').trim()
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : ''
})

watchDynamicTitle(
  () => [model.value?.nome, activeImage.value],
  () => {
    if (!model.value?.nome) return null
    return {
      title: model.value.nome,
      description: (model.value.descricao || 'Detalhe do produto Diomika.').slice(0, 160),
      image: displayImage.value,
      path: route.fullPath,
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

const fetchProduct = async () => {
  try {
    loading.value = true
    error.value = null
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
      const currentModelKey = String(route.params.modelSlug || route.params.legacyModelId || '').trim()
      const canonicalModelKey = String(canonical.params?.modelSlug || '').trim()
      if (legacyId || (currentModelKey && canonicalModelKey && currentModelKey !== canonicalModelKey)) {
        await router.replace(canonical)
        return
      }
    }

    const rawColors = (modelData.modelo_cores || [])
      .filter((c) => c.visibilidade !== false)
      .sort((a, b) => a.numero - b.numero)
    const colorUrls = await resolveImageUrls(rawColors.map((c) => c.imagem), PLACEHOLDER)
    colors.value = rawColors.map((c, i) => ({ ...c, imagem: colorUrls[i] || PLACEHOLDER }))

    if (colors.value.length === 0) {
      throw new Error('Não existem cores disponíveis para este modelo.')
    }

    pickerOptions.value = catalog.buildPickerOptions(modelData, storefrontCtx.value)
    if (pickerOptions.value.length === 0) {
      const label = storefrontCtx.value?.picker?.label || 'variante'
      throw new Error(`Não existem ${label.toLowerCase()} disponíveis para este modelo.`)
    }

    if (singleProductMode.value) {
      const product = selectedProduct.value
      if (!product) {
        throw new Error('Este modelo ainda não tem EAN registado.')
      }
      const pt = storefrontCtx.value.product_table
      const [barcodeUrl] = product.barcode_url
        ? await resolveImageUrls([product.barcode_url], '')
        : ['']
      model.value[pt] = {
        ...product,
        barcode_url: barcodeUrl,
      }
    } else {
      const barcodePaths = pickerOptions.value.map((opt) => opt.value?.barcode_url || '')
      const barcodeUrls = await resolveImageUrls(barcodePaths, '')
      pickerOptions.value = pickerOptions.value.map((opt, i) => ({
        ...opt,
        value: {
          ...opt.value,
          barcode_url: barcodeUrls[i] || '',
        },
      }))
    }

    selectColor(colors.value[0])
    selectPicker(pickerOptions.value[0])
    selectedQty.value = qtyMin.value
  } catch (err) {
    error.value = 'Não foi possível carregar os detalhes do produto.'
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

  const picker = storefrontCtx.value?.picker
  const dimLabel = singleProductMode.value
    ? selectedPicker.value.label
    : product[picker?.field || 'dimensoes']

  cart.addItem({
    ean: product.ean,
    numero_cor: selectedColor.value.numero,
    altura: product.altura || (singleProductMode.value ? selectedPicker.value.value : undefined),
    quantidade: selectedQty.value,
    modeloNome: model.value.nome,
    dimensoes: dimLabel,
    corNome: selectedColor.value.nome,
    carrinhoStep: qtyStep.value,
    carrinhoMin: qtyMin.value,
    imagem: selectedColor.value.imagem,
  })

  addedMsg.value = `${selectedQty.value} un. adicionadas ao pedido.`
  setTimeout(() => {
    addedMsg.value = ''
  }, 2800)
}

const goToCart = () => router.push({ name: 'cart' })

onMounted(fetchProduct)
watch(() => route.fullPath, fetchProduct)
</script>

<template>
  <div class="product-detail">
    <Breadcrumbs :items="breadcrumbItems" />

    <LoadingState v-if="loading" message="A carregar detalhes…" />
    <p v-else-if="error" class="alert alert-error page-shell">{{ error }}</p>

    <article
      v-else-if="model && selectedColor && selectedPicker"
      class="detail-layout page-shell"
    >
      <section class="gallery">
        <button type="button" class="main-image-wrap" aria-label="Ampliar imagem" @click="lightboxOpen = true">
          <SoftImage
            :src="displayImage"
            :alt="`${model.nome} — cor seleccionada`"
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
              :key="c.id"
              type="button"
              class="color-thumb-btn"
              :class="{ active: selectedColor.id === c.id }"
              :title="c.nome || `Cor ${c.numero}`"
              @click="selectColor(c)"
            >
              <SoftImage :src="c.imagem || PLACEHOLDER" :alt="c.nome || `Cor ${c.numero}`" thumb />
            </button>
          </div>
        </div>
      </section>

      <section class="buy-column">
        <header class="product-header">
          <RouterLink
            v-if="category"
            class="cat-link"
            :to="categoryProductsRoute(category)"
          >
            {{ categoryName }}
          </RouterLink>
          <span v-if="badgeText" class="badge-pill badge-soft">{{ badgeText }}</span>
          <h1>{{ model.nome }}</h1>
          <p v-if="model.descricao" class="product-desc">{{ model.descricao }}</p>
          <p v-else class="product-desc">
            Seleccione a cor{{ storefrontCtx?.picker ? ` e a ${String(storefrontCtx.picker.label || 'variante').toLowerCase()}` : '' }},
            indique a quantidade e adicione ao pedido de orçamento.
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

          <label class="field-label qty-block">
            Quantidade
            <QtySelect v-model="selectedQty" :step="qtyStep" :min="qtyMin" />
          </label>

          <div class="cart-actions">
            <button type="button" class="btn btn-primary btn-block" @click="addToCart">
              Adicionar ao pedido
            </button>
            <button type="button" class="btn btn-secondary btn-block" @click="goToCart">
              Ver pedido
            </button>
          </div>

          <p v-if="addedMsg" class="added-msg" role="status">{{ addedMsg }}</p>

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
    <ImageLightbox :open="lightboxOpen" :src="displayImage" :alt="model?.nome || 'Produto Diomika'" @close="lightboxOpen = false" />
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
  transition: border-color var(--transition), transform var(--transition);
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
