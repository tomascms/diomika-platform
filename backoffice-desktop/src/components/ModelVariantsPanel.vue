<script setup>
import { ref, watch, computed } from 'vue'
import { api } from '@/lib/api'

const props = defineProps({
  modelId: { type: String, default: null },
  productTable: { type: String, default: null },
  readOnly: { type: Boolean, default: false },
})

const rows = ref([])
const loading = ref(false)
const error = ref('')
// O único atributo específico da variante desta família (ex.: "dimensoes" para
// almofadas, "altura" para assentos) — descoberto a partir do form schema da
// tabela de produto. A maioria das famílias não tem nenhum (ex.: guarda-chuvas).
const extraField = ref(null)

const emptyRow = () => ({ id: null, ean: '', extra: '' })

async function mapPool(items, concurrency, fn) {
  if (!items.length) return []
  const results = new Array(items.length)
  let next = 0
  const workers = Array.from({ length: Math.min(concurrency, items.length) }, async () => {
    while (next < items.length) {
      const idx = next++
      results[idx] = await fn(items[idx], idx)
    }
  })
  await Promise.all(workers)
  return results
}

const loadExtraField = async () => {
  extraField.value = null
  if (!props.productTable) return
  try {
    const schema = await api.formSchema(props.productTable)
    const field = (schema.fields || []).find(
      (f) => !['id_modelo', 'ean', 'visibilidade'].includes(f.name),
    )
    extraField.value = field || null
  } catch {
    extraField.value = null
  }
}

const load = async () => {
  rows.value = []
  await loadExtraField()
  if (!props.modelId || !props.productTable) {
    if (!props.readOnly) rows.value = [emptyRow()]
    return
  }
  loading.value = true
  error.value = ''
  try {
    const data = await api.listRecords(props.productTable, { id_modelo: props.modelId, limit: '100' })
    rows.value = data.length
      ? data.map((p) => ({
          id: p.id,
          ean: p.ean || '',
          extra: extraField.value ? (p.attributes || {})[extraField.value.name] || '' : '',
        }))
      : props.readOnly
        ? []
        : [emptyRow()]
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
    } catch (e) {
      error.value = e.message
      return
    }
  }
  rows.value.splice(idx, 1)
  if (!rows.value.length && !props.readOnly) rows.value.push(emptyRow())
}

const save = async (modelId, { publish = false } = {}) => {
  if (props.readOnly || !modelId || !props.productTable) return
  error.value = ''
  const keptIds = new Set()
  const toSave = rows.value.filter((row) => String(row.ean || '').trim())
  if (publish && !toSave.length) {
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

  await mapPool(toSave, 4, async (row) => {
    const payload = {
      id_modelo: modelId,
      ean: String(row.ean).trim(),
      attributes: extraField.value ? { [extraField.value.name]: row.extra } : {},
      visibilidade: publish,
    }
    if (row.id) {
      await api.updateRecord(props.productTable, row.id, { ...payload, id: row.id })
      keptIds.add(row.id)
    } else {
      const created = await api.createRecord(props.productTable, payload)
      row.id = created.id
      keptIds.add(created.id)
    }
  })

  if (props.modelId) {
    const existing = await api.listRecords(props.productTable, { id_modelo: modelId, limit: '100' })
    const orphans = existing.filter((p) => !keptIds.has(p.id))
    await mapPool(orphans, 4, (p) => api.deleteRecord(props.productTable, p.id, true))
  }

  await load()
}

const eanPlaceholder = computed(() => 'ex: 5600000000013')

defineExpose({ save })
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
