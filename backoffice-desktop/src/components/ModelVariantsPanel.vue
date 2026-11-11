<script setup>
import { ref, watch, computed } from 'vue'
import { api } from '@/lib/api'
import { variantItems } from '@/lib/bundle'

const props = defineProps({
  modelId: { type: String, default: null },
  productTable: { type: String, default: null },
  readOnly: { type: Boolean, default: false },
  // Do formulário agregado (/admin/form): linhas e campos da variante — evita 2 pedidos ao abrir.
  initialRows: { type: Array, default: null },
  variantFields: { type: Array, default: null },
})

const rows = ref([])
const loading = ref(false)
const error = ref('')
// O único atributo específico da variante desta família (ex.: "dimensoes" para
// almofadas, "altura" para assentos) — descoberto a partir do form schema da
// tabela de produto. A maioria das famílias não tem nenhum (ex.: guarda-chuvas).
const extraField = ref(null)
// Estado gravado por id: só se envia o que mudou (antes: um PUT por EAN a cada gravação).
let saved = new Map()

const emptyRow = () => ({ id: null, ean: '', extra: '', vis: false })
const pickExtraField = (fields) =>
  (fields || []).find((f) => !['id_modelo', 'ean', 'visibilidade'].includes(f.name)) || null
const toRow = (p) => ({
  id: p.id,
  ean: p.ean || '',
  extra: extraField.value ? (p.attributes || {})[extraField.value.name] || '' : '',
  vis: p.visibilidade === true,
})
const contentKey = (row, vis) => JSON.stringify([String(row.ean || '').trim(), String(row.extra || ''), Boolean(vis)])

const setRows = (data) => {
  rows.value = data.length ? data.map(toRow) : props.readOnly ? [] : [emptyRow()]
  saved = new Map(rows.value.filter((r) => r.id).map((r) => [r.id, contentKey(r, r.vis)]))
}

const loadExtraField = async () => {
  if (props.variantFields) return pickExtraField(props.variantFields)
  if (!props.productTable) return null
  try {
    return pickExtraField((await api.formSchema(props.productTable)).fields)
  } catch {
    return null
  }
}

let usedInitial = false
const load = async () => {
  const useInitial = props.initialRows && !usedInitial
  usedInitial = usedInitial || Boolean(props.initialRows)
  if (!props.modelId || !props.productTable) {
    extraField.value = await loadExtraField()
    rows.value = props.readOnly ? [] : [emptyRow()]
    saved = new Map()
    return
  }
  loading.value = true
  error.value = ''
  try {
    // Em paralelo (antes: schema e depois lista, em série).
    const [field, data] = await Promise.all([
      loadExtraField(),
      useInitial ? props.initialRows : api.listRecords(props.productTable, { id_modelo: props.modelId, limit: '100' }),
    ])
    extraField.value = field
    setRows(data)
  } catch (e) {
    error.value = e.message
    if (!props.readOnly) rows.value = [emptyRow()]
  } finally {
    loading.value = false
  }
}

watch(() => [props.modelId, props.productTable], load, { immediate: true })

const addRow = () => rows.value.push(emptyRow())

// Tirar um produto da lista só o apaga ao gravar (dentro do mesmo pedido atómico do modelo).
let removed = []
const removeRow = (idx) => {
  const row = rows.value[idx]
  if (row.id && !confirm('Eliminar este produto (EAN)? Sai da loja quando gravar o modelo.')) return
  if (row.id && saved.has(row.id)) removed.push(row.id)
  rows.value.splice(idx, 1)
  if (!rows.value.length && !props.readOnly) rows.value.push(emptyRow())
}

/**
 * Prepara os produtos para o pedido do modelo (não grava): valida e devolve `{ items, deleteIds }`.
 * Depois de o pedido ter sucesso, `commit()` marca-os como gravados.
 */
const collect = ({ visible = false, requireRows = false } = {}) => {
  if (props.readOnly || !props.productTable) return { items: [], deleteIds: [] }
  error.value = ''
  const items = variantItems(rows.value, {
    extraField: extraField.value,
    visible,
    requireRows,
    newId: () => crypto.randomUUID(),
  })
  const withEan = rows.value.filter((row) => String(row.ean || '').trim())
  items.forEach((item, i) => {
    withEan[i].id = item.id // `items` sai pela mesma ordem das linhas com EAN
  })
  return { items, deleteIds: [...removed] }
}

const commit = (visible) => {
  removed = []
  saved = new Map(rows.value.filter((r) => r.id).map((r) => [r.id, contentKey(r, visible)]))
  for (const row of rows.value) row.vis = visible
}

const eanPlaceholder = computed(() => 'ex: 5600000000013')

/** EAN gravados (para o aviso «Para aparecer na loja»). */
const savedWithEan = computed(() => rows.value.filter((r) => r.id && String(r.ean || '').trim()).length)

defineExpose({ collect, commit, savedWithEan })
</script>

<template>
  <section class="variants-panel">
    <h3>Produtos (EAN)</h3>
    <p class="hint">
      Pelo menos um produto com EAN<template v-if="extraField"> e {{ extraField.label.toLowerCase() }}</template>.
    </p>
    <p v-if="loading" class="muted">A carregar produtos…</p>
    <p v-if="error" class="err">{{ error }}</p>

    <article v-for="(row, idx) in rows" :key="row.id || `new-${idx}`" class="variant-row card">
      <div class="fields">
        <input
          v-model="row.ean"
          class="input ean"
          placeholder="EAN-13"
          :title="eanPlaceholder"
          maxlength="13"
          :disabled="readOnly"
        />
        <input
          v-if="extraField"
          v-model="row.extra"
          class="input"
          :placeholder="extraField.placeholder || extraField.label"
          :disabled="readOnly || (Boolean(row.id) && extraField.lock_on_edit)"
        />
      </div>
      <button v-if="!readOnly" type="button" class="btn btn-danger btn-sm" @click="removeRow(idx)">X</button>
    </article>

    <button v-if="!readOnly" type="button" class="btn btn-ghost" @click="addRow">+ Adicionar produto</button>
  </section>
</template>

<style scoped>
.variants-panel { margin-top: 28px; padding-top: 20px; border-top: 1px solid var(--border); display: grid; gap: 12px; }
.hint, .muted { margin: 0; font-size: 0.85rem; color: var(--text-muted); }
.err { color: var(--danger); margin: 0; }
.variant-row { padding: 14px; display: flex; gap: 12px; align-items: flex-start; }
.fields { flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.ean { font-variant-numeric: tabular-nums; }
.btn-sm { padding: 6px 10px; }
</style>
