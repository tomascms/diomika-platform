<script setup>
defineOptions({ name: 'TableView' })

import { ref, computed, watch, onMounted, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/lib/api'
import { useWorkspace } from '@/composables/useWorkspace'
import { useAggregatedTipos } from '@/composables/useAggregatedTipos'
import DataList from '@/components/DataList.vue'
import CategoryCreatePanel from '@/components/CategoryCreatePanel.vue'

const PAGE_SIZE = 40

const route = useRoute()
const router = useRouter()
const { tableConfig, workspace } = useWorkspace()
const { getAggregatedTiposForCategory } = useAggregatedTipos()

const rows = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const error = ref('')
const message = ref('')
const filterText = ref('')
const filterCategoriaId = ref('')
const filterModeloId = ref('')
const showNewPicker = ref(false)
const showCategoryCreate = ref(false)
const importInput = ref(null)
const importBusy = ref(false)
const categories = ref([])
const newCategoryId = ref('')
const listOffset = ref(0)
const hasMore = ref(false)
const totalApprox = ref(null)
let loadSeq = 0

const table = computed(() => route.params.table)
const isCategories = computed(() => table.value === 'categories')
const cfg = computed(() => tableConfig(table.value) || workspace.value?.sidebar?.[table.value])
const isMerged = computed(() => {
  if (table.value === 'produtos' || table.value === 'modelos') return true
  return Boolean(cfg.value?.ui_catalog_merged_list)
})
const sectionLabel = computed(() => cfg.value?.label || table.value)
const canShowNew = computed(() => !isCategories.value)
const canImportExport = computed(() => !isCategories.value && !isMerged.value)

const catalogTypes = computed(() => workspace.value?.catalog?.catalog_types || [])
const categoryDefinitions = computed(() => workspace.value?.catalog?.category_definitions || {})

// Esquema unificado: a relação "modelo" embutida numa linha de produto vem
// sempre sob o nome físico da tabela (product_models), seja qual for a
// família — já não é preciso adivinhar entre N tabelas.
const embeddedModel = (row) => row?.product_models || null

const recordLabel = (row) => {
  if (table.value === 'produtos') {
    const model = embeddedModel(row)
    const attrs = row.attributes || {}
    const parts = [model?.nome, attrs.dimensoes, attrs.altura, attrs.segmento, row.ean].filter(Boolean)
    return parts.join(' · ') || '—'
  }
  return row.nome || row.ean || String(row.id).slice(0, 8)
}

const categoryLabel = (row) => {
  if (row.categories?.nome) return row.categories.nome
  const model = embeddedModel(row)
  if (model?.categories?.nome) return model.categories.nome
  if (row._categoria_label) return row._categoria_label
  return '—'
}

const rowSearchText = (row) => {
  const model = embeddedModel(row)
  const attrs = row.attributes || {}
  const parts = [
    row.nome,
    row.ean,
    attrs.dimensoes,
    attrs.altura,
    attrs.segmento,
    row.slug,
    row._categoria_label,
    row.categories?.nome,
    model?.nome,
    model?.categories?.nome,
    row._ptable,
  ]
  return parts.filter(Boolean).join(' ').toLowerCase()
}

const columns = computed(() => {
  if (isMerged.value) {
    return [
      { key: 'nome', label: table.value === 'produtos' ? 'Produto' : 'Modelo', format: recordLabel },
      { key: '_categoria', label: 'Categoria', format: categoryLabel },
    ]
  }
  const fields = tableConfig(table.value)?.list_label_fields || ['nome']
  if (isCategories.value) {
    return [{ key: 'nome', label: 'Nome', format: (row) => String(row.nome || '').trim() || '—' }]
  }
  return fields.map((f) => ({ key: f, label: f.replace(/_/g, ' ') }))
})

const filteredRows = computed(() => {
  if (!isMerged.value) return rows.value
  const q = filterText.value.trim().toLowerCase()
  if (!q) return rows.value
  return rows.value.filter((r) => rowSearchText(r).includes(q))
})

const newPhysicalTipo = ref('')

const mergedListParams = computed(() => {
  const params = {}
  if (filterCategoriaId.value) params.categoria_id = filterCategoriaId.value
  if (filterModeloId.value) params.modelo_id = filterModeloId.value
  const cat = categories.value.find((c) => String(c.id) === String(filterCategoriaId.value))
  if (cat?.tipo_catalogo) params.tipo_catalogo = cat.tipo_catalogo
  return params
})

const selectedCategory = computed(() =>
  categories.value.find((c) => c.id === newCategoryId.value) || null,
)


const isAggregatedCategory = computed(() => Boolean(getAggregatedTiposForCategory(selectedCategory.value)))

const loadRows = async ({ append = false } = {}) => {
  const seq = ++loadSeq
  if (append) loadingMore.value = true
  else {
    loading.value = true
    listOffset.value = 0
    hasMore.value = false
    totalApprox.value = null
  }
  error.value = ''
  try {
    if (isMerged.value) {
      const viewKey = table.value === 'produtos' ? 'produtos' : 'modelos'
      const offset = append ? listOffset.value : 0
      const page = await api.mergedList(viewKey, {
        ...mergedListParams.value,
        limit: String(PAGE_SIZE),
        offset: String(offset),
      })
      if (seq !== loadSeq) return
      const items = page.items || []
      rows.value = append ? [...rows.value, ...items] : items
      listOffset.value = offset + items.length
      totalApprox.value = page.total_approx ?? null
      hasMore.value = items.length >= PAGE_SIZE && (
        totalApprox.value == null || listOffset.value < totalApprox.value
      )
    } else {
      const offset = append ? listOffset.value : 0
      const params = {
        visible_only: 'false',
        limit: String(PAGE_SIZE),
        offset: String(offset),
      }
      const q = filterText.value.trim()
      if (q) params.q = q
      const page = await api.listRecordsPage(table.value, params)
      if (seq !== loadSeq) return
      const items = page.items || []
      rows.value = append ? [...rows.value, ...items] : items
      listOffset.value = offset + items.length
      hasMore.value = items.length >= PAGE_SIZE
    }
  } catch (e) {
    if (seq !== loadSeq) return
    error.value = e.message
    // Não limpar rows existentes — evita «Sem registos» falso em falhas transitórias
  } finally {
    if (seq === loadSeq) {
      loading.value = false
      loadingMore.value = false
    }
  }
}

const loadMore = () => {
  if (!hasMore.value || loadingMore.value || loading.value) return
  return loadRows({ append: true })
}

const onCategoryCreated = async () => {
  message.value = 'Categoria criada.'
  error.value = ''
  showCategoryCreate.value = false
  await loadRows()
}

// Mensagens de sucesso desaparecem sozinhas; erros ficam até à próxima acção.
let messageTimer = null
watch(message, (text) => {
  clearTimeout(messageTimer)
  if (text) messageTimer = setTimeout(() => { message.value = '' }, 3500)
})

const openRow = (row) => {
  const ptable = row._ptable || table.value
  router.push({ name: 'record-edit', params: { table: ptable, id: row.id } })
}

const toggleVisibility = async (row) => {
  const ptable = row._ptable || table.value
  const next = row.visibilidade === false
  try {
    await api.setVisibility(ptable, row.id, next)
    row.visibilidade = next
    message.value = next ? 'Registo visível.' : 'Registo oculto.'
  } catch (e) {
    error.value = e.message
  }
}

const deleteRow = async (row) => {
  const ptable = row._ptable || table.value
  const ok = confirm(
    'Apagar este registo da base de dados?\n\nEsta acção não pode ser desfeita.\nPara ocultar sem apagar, use o botão Visível/Oculto.',
  )
  if (!ok) return
  try {
    await api.deleteRecord(ptable, row.id, true)
    rows.value = rows.value.filter((r) => r.id !== row.id)
    message.value = 'Registo eliminado.'
  } catch (e) {
    error.value = e.message
  }
}

const physicalTableForCategory = (categoryId, physicalTipo = null) => {
  const cat = categories.value.find((c) => c.id === categoryId)
  if (!cat?.tipo_catalogo) return null
  const aggregated = getAggregatedTiposForCategory(cat)
  const tipo = physicalTipo || cat.tipo_catalogo
  if (aggregated && !physicalTipo) return null
  const ct = catalogTypes.value.find((t) => t.tipo === tipo)
  if (!ct) return null
  return table.value === 'produtos' ? ct.product_table : ct.model_table
}

const startNew = async () => {
  if (isMerged.value) {
    if (!categories.value.length) {
      categories.value = await api.listCategoriesForForms()
    }
    newCategoryId.value = ''
    newPhysicalTipo.value = ''
    showNewPicker.value = true
    return
  }
  router.push({ name: 'record-new', params: { table: table.value } })
}

const confirmNew = () => {
  if (!newCategoryId.value) {
    error.value = 'Escolha uma categoria.'
    return
  }
  const cat = selectedCategory.value
  const aggregated = getAggregatedTiposForCategory(cat)
  if (aggregated && !newPhysicalTipo.value) {
    error.value = 'Escolha a família de produto.'
    return
  }
  const physicalTable = physicalTableForCategory(newCategoryId.value, newPhysicalTipo.value || null)
  if (!physicalTable) {
    error.value = 'Categoria inválida ou tipo de catálogo em falta.'
    return
  }
  router.push({
    name: 'record-new-physical',
    params: { table: table.value, physicalTable },
    query: { id_categoria: newCategoryId.value },
  })
}

const exportTable = async () => {
  try {
    const blob = await api.exportCsv(table.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${table.value}.csv`
    a.click()
    URL.revokeObjectURL(url)
    message.value = 'Exportação concluída.'
  } catch (e) {
    error.value = e.message
  }
}

const triggerImport = () => importInput.value?.click()

const onImportFile = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  importBusy.value = true
  error.value = ''
  message.value = ''
  try {
    const preview = await api.importCsv(table.value, file, true)
    const ok = confirm(`Pré-visualização: ${preview.created} linhas válidas.\nImportar para a base de dados?`)
    if (!ok) return
    const result = await api.importCsv(table.value, file, false)
    message.value = `Importação: ${result.created} criados, ${result.updated} actualizados.`
    await loadRows()
  } catch (e) {
    error.value = e.message
  } finally {
    importBusy.value = false
  }
}

const filterModeloOptions = ref([])

const loadModeloFilterOptions = async () => {
  filterModeloOptions.value = []
  filterModeloId.value = ''
  if (table.value !== 'produtos' || !filterCategoriaId.value) return
  try {
    const page = await api.mergedList('modelos', {
      categoria_id: filterCategoriaId.value,
      tipo_catalogo: categories.value.find((c) => String(c.id) === String(filterCategoriaId.value))?.tipo_catalogo || '',
      limit: '100',
      offset: '0',
    })
    filterModeloOptions.value = (page.items || []).map((m) => ({
      id: m.id,
      label: m.nome || String(m.id).slice(0, 8),
    }))
  } catch {
    filterModeloOptions.value = []
  }
}

const ensureCategories = async () => {
  if (!isMerged.value || categories.value.length) return
  try {
    categories.value = await api.listCategoriesForForms()
  } catch {
    categories.value = []
  }
}

watch(table, (next, prev) => {
  showCategoryCreate.value = false
  showNewPicker.value = false
  message.value = ''
  error.value = ''
  filterCategoriaId.value = ''
  filterModeloId.value = ''
  filterText.value = ''
  filterModeloOptions.value = []
  if (prev !== undefined && next !== prev) {
    rows.value = []
    hasMore.value = false
    totalApprox.value = null
  }
  void loadRows()
  void ensureCategories()
}, { immediate: true })

watch([filterCategoriaId, filterModeloId], () => {
  if (isMerged.value) void loadRows()
})

watch(filterCategoriaId, () => {
  if (table.value === 'produtos') void loadModeloFilterOptions()
})

let filterDebounce = null
watch(filterText, () => {
  if (isMerged.value) return
  clearTimeout(filterDebounce)
  filterDebounce = setTimeout(() => void loadRows(), 300)
})

onMounted(() => {
  void ensureCategories()
})

onActivated(() => {
  void ensureCategories()
})
</script>

<template>
  <div class="page-view">
    <div class="toolbar toolbar-panel">
      <input v-model="filterText" class="input search" type="search" placeholder="Pesquisar…" aria-label="Pesquisar registos" />
      <template v-if="isMerged">
        <select v-model="filterCategoriaId" class="input filter-mini" aria-label="Filtrar por categoria">
          <option value="">Todas as categorias</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">
            {{ c.nome }}{{ c.visibilidade === false ? ' (oculta no site)' : '' }}
          </option>
        </select>
        <select
          v-if="table === 'produtos'"
          v-model="filterModeloId"
          class="input filter-mini"
          :disabled="!filterCategoriaId"
          aria-label="Filtrar por modelo"
        >
          <option value="">Todos os modelos</option>
          <option v-for="m in filterModeloOptions" :key="m.id" :value="m.id">{{ m.label }}</option>
        </select>
      </template>
      <button
        v-if="isCategories"
        type="button"
        class="btn btn-primary"
        :aria-expanded="showCategoryCreate"
        @click="showCategoryCreate = !showCategoryCreate"
      >
        {{ showCategoryCreate ? 'Fechar' : 'Nova categoria' }}
      </button>
      <button v-if="canShowNew" type="button" class="btn btn-primary" @click="startNew">Novo registo</button>
      <template v-if="canImportExport">
        <button class="btn btn-ghost" @click="exportTable">Exportar CSV</button>
        <button class="btn btn-ghost" :disabled="importBusy" @click="triggerImport">
          {{ importBusy ? 'A importar…' : 'Importar CSV' }}
        </button>
        <input ref="importInput" type="file" accept=".csv,text/csv" class="hidden-file" @change="onImportFile" />
      </template>
    </div>

    <CategoryCreatePanel
      v-if="isCategories && showCategoryCreate"
      @created="onCategoryCreated"
      @error="error = $event"
    />

    <div v-if="showNewPicker" class="card picker">
      <h3>Novo registo — {{ sectionLabel }}</h3>
      <label>Categoria</label>
      <select v-model="newCategoryId" class="input">
        <option value="">— Escolher categoria —</option>
        <option v-for="c in categories" :key="c.id" :value="c.id">
          {{ c.nome }}{{ c.visibilidade === false ? ' (oculta no site)' : '' }}
        </option>
      </select>
      <template v-if="isAggregatedCategory">
        <label>Família</label>
        <select v-model="newPhysicalTipo" class="input">
          <option value="">— Escolher família —</option>
          <option
            v-for="tipo in getAggregatedTiposForCategory(selectedCategory)"
            :key="tipo"
            :value="tipo"
          >
            {{ catalogTypes.find((t) => t.tipo === tipo)?.label || tipo }}
          </option>
        </select>
      </template>
      <div class="picker-actions">
        <button class="btn btn-ghost" @click="showNewPicker = false">Cancelar</button>
        <button class="btn btn-primary" @click="confirmNew">Continuar</button>
      </div>
    </div>

    <p v-if="message" class="ok" role="status">{{ message }}</p>
    <p v-if="error" class="err" role="alert">{{ error }}</p>

    <DataList
      :rows="filteredRows"
      :columns="columns"
      :loading="loading"
      @open="openRow"
      @toggle-visibility="toggleVisibility"
      @delete="deleteRow"
    />

    <div v-if="isMerged && rows.length" class="pager">
      <p class="pager-meta">
        A mostrar {{ rows.length }}{{ totalApprox != null ? ` de ~${totalApprox}` : '' }} registos
      </p>
      <button
        v-if="hasMore"
        type="button"
        class="btn btn-ghost"
        :disabled="loadingMore || loading"
        @click="loadMore"
      >
        {{ loadingMore ? 'A carregar…' : 'Carregar mais' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.page-view {
  display: grid;
  gap: 14px;
  max-width: 1100px;
}

.toolbar-panel {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.input.search {
  flex: 1 1 260px;
  width: auto;
  min-width: 200px;
}

.input.filter-mini {
  flex: 0 1 220px;
  width: auto;
}

.hidden-file {
  display: none;
}

.picker {
  display: grid;
  gap: 8px;
  max-width: 520px;
  padding: 18px 20px;
}

.picker h3 {
  margin-bottom: 4px;
}

.picker label {
  margin-top: 6px;
  font-size: 13px;
  font-weight: 560;
  color: var(--text-secondary);
}

.picker-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}

.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.pager-meta {
  font-size: 12.5px;
  color: var(--text-muted);
}
</style>
