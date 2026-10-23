<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: [Object, String], default: () => ({}) },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const rows = ref([{ material: '', percent: '' }])
let syncing = false

const parseValue = (val) => {
  if (!val) return [{ material: '', percent: '' }]
  let parsed = val
  if (typeof val === 'string') {
    try {
      parsed = JSON.parse(val)
    } catch {
      return [{ material: '', percent: '' }]
    }
  }
  if (typeof parsed === 'object' && !Array.isArray(parsed)) {
    const entries = Object.entries(parsed)
    return entries.length
      ? entries.map(([material, percent]) => ({
          material: String(material),
          percent: String(percent ?? ''),
        }))
      : [{ material: '', percent: '' }]
  }
  return [{ material: '', percent: '' }]
}

watch(
  () => props.modelValue,
  (v) => {
    if (syncing) return
    rows.value = parseValue(v)
  },
  { immediate: true },
)

const buildPayload = () => {
  const out = {}
  for (const r of rows.value) {
    const m = String(r.material ?? '').trim()
    const pRaw = String(r.percent ?? '').trim()
    if (!m || !pRaw) continue
    const p = parseInt(pRaw, 10)
    if (!Number.isFinite(p) || p < 0) continue
    out[m] = p
  }
  return out
}

/** Total visual: soma % das linhas (mesmo sem material ainda). */
const totalUi = computed(() =>
  rows.value.reduce((sum, r) => sum + (parseInt(String(r.percent ?? ''), 10) || 0), 0),
)

const totalSaved = computed(() =>
  Object.values(buildPayload()).reduce((sum, p) => sum + p, 0),
)

const sync = () => {
  syncing = true
  emit('update:modelValue', buildPayload())
  queueMicrotask(() => {
    syncing = false
  })
}

const addRow = () => {
  rows.value.push({ material: '', percent: '' })
}

const removeRow = (idx) => {
  rows.value.splice(idx, 1)
  if (!rows.value.length) rows.value.push({ material: '', percent: '' })
  sync()
}
</script>

<template>
  <div class="composition">
    <div v-for="(row, idx) in rows" :key="idx" class="row">
      <input
        v-model="row.material"
        class="input"
        placeholder="Material (ex: algodão)"
        :disabled="disabled"
        @input="sync"
      />
      <input
        v-model="row.percent"
        class="input pct"
        type="number"
        min="0"
        max="100"
        placeholder="%"
        :disabled="disabled"
        @input="sync"
      />
      <button v-if="!disabled" type="button" class="btn btn-danger btn-sm" @click="removeRow(idx)">X</button>
    </div>
    <button v-if="!disabled" type="button" class="btn btn-ghost btn-sm" @click="addRow">+ Adicionar material</button>
    <p class="sum" :class="{ ok: totalSaved === 100, warn: totalSaved !== 100 }">
      Total a gravar: {{ totalSaved }}%
      <span v-if="totalUi !== totalSaved"> (a escrever: {{ totalUi }}%)</span>
      — deve ser 100%
    </p>
  </div>
</template>

<style scoped>
.composition { display: grid; gap: 8px; padding: 12px; background: var(--bg-hover); border-radius: var(--radius); }
.row { display: flex; gap: 8px; align-items: center; }
.pct { width: 72px; flex-shrink: 0; }
.btn-sm { padding: 6px 10px; font-size: 0.8rem; }
.sum { margin: 4px 0 0; font-size: 0.8rem; }
.sum.ok { color: var(--success); }
.sum.warn { color: var(--danger); }
</style>
