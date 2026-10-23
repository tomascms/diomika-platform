<script setup>
import { ref, watch, computed } from 'vue'
import { api } from '@/lib/api'
import { mapPool } from '@/lib/pool'

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

const removeRow = async (idx) => {
  const row = rows.value[idx]
  if (row.id && !confirm('Eliminar este produto (EAN)?')) return
  if (row.id && props.productTable) {
    try {
      await api.deleteRecord(props.productTable, row.id, true)
      saved.delete(row.id)
    } catch (e) {
      error.value = e.message
      return
    }
  }
  rows.value.splice(idx, 1)
  if (!rows.value.length && !props.readOnly) rows.value.push(emptyRow())
}

/**
 * Grava os EAN com a visibilidade `visible` (a do modelo depois de gravar).
 * Só cria/actualiza linhas novas ou alteradas; no fim remove do servidor EAN que já não estão na lista.
 */
const save = async (modelId, { visible = false, requireRows = false } = {}) => {
  if (props.readOnly || !modelId || !props.productTable) return
  error.value = ''
  const toSave = rows.value.filter((row) => String(row.ean || '').trim())
  if (requireRows && !toSave.length) {
    throw new Error('Adicione pelo menos um produto (EAN) antes de publicar na loja.')
  }

  for (const row of toSave) {
    if (!/^\d{13}$/.test(String(row.ean).trim())) {
      throw new Error(`EAN «${row.ean}» inválido — tem de ter 13 dígitos.`)
    }
    if (extraField.value?.required && !String(row.extra || '').trim()) {
      throw new Error(`EAN ${row.ean}: indique ${extraField.value.label.toLowerCase()}.`)
    }
  }

  const dirty = toSave.filter((row) => !row.id || saved.get(row.id) !== contentKey(row, visible))
  await mapPool(dirty, 4, async (row) => {
    const payload = {
      id_modelo: modelId,
      ean: String(row.ean).trim(),
      attributes: extraField.value ? { [extraField.value.name]: row.extra } : {},
      visibilidade: visible,
    }
    if (row.id) {
      await api.updateRecord(props.productTable, row.id, { ...payload, id: row.id })
    } else {
      const created = await api.createRecord(props.productTable, payload)
      row.id = created.id
    }
    row.vis = visible
    saved.set(row.id, contentKey(row, visible))
  })

  // Uma só leitura: limpa duplicados de tentativas anteriores e recarrega a lista.
  const keptIds = new Set(toSave.map((r) => r.id))
  const existing = await api.listRecords(props.productTable, { id_modelo: modelId, limit: '100' })
  const orphans = existing.filter((p) => !keptIds.has(p.id))
  await mapPool(orphans, 4, (p) => api.deleteRecord(props.productTable, p.id, true))
  setRows(existing.filter((p) => keptIds.has(p.id)))
}

const eanPlaceholder = computed(() => 'ex: 5600000000013')

/** EAN gravados (para o aviso «Para aparecer na loja»). */
const savedWithEan = computed(() => rows.value.filter((r) => r.id && String(r.ean || '').trim()).length)

defineExpose({ save, savedWithEan })
</script>

<template>
  <section class="variants-panel">
    <h3>Produtos (EAN)</h3>
    <p class="hint">
      Obrigatório para aparecer na loja: pelo menos um produto com EAN
      <template v-if="extraField"> e {{ extraField.label.toLowerCase() }}</template>.
      Já não é preciso sair desta página para os criar à parte.
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
