<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '@/lib/api'
import DataList from '@/components/DataList.vue'
import OrderRecordPanel from '@/components/OrderRecordPanel.vue'

const rows = ref([])
const selected = ref(null)
const loading = ref(true)
const error = ref('')
const message = ref('')

const columns = [
  { key: 'nome', label: 'Cliente', format: (r) => r.nome || r.referencia_cliente || '—' },
  { key: 'email', label: 'Email' },
]

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    rows.value = await api.listRecords('pedidos_orcamento', { visible_only: 'false' })
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const openRow = async (row) => {
  selected.value = row
  if (!row.lida) {
    try {
      await api.setLida('pedidos_orcamento', row.id, true)
      row.lida = true
    } catch (e) {
      error.value = e.message
    }
  }
}

const toggleRead = async (row) => {
  const next = !row.lida
  try {
    await api.setLida('pedidos_orcamento', row.id, next)
    row.lida = next
    if (selected.value?.id === row.id) selected.value = { ...row, lida: next }
  } catch (e) {
    error.value = e.message
  }
}

const deleteRow = async (row) => {
  if (
    !confirm(
      'Apagar este orçamento da base de dados?\n\nEsta acção não pode ser desfeita.',
    )
  ) {
    return
  }
  try {
    await api.deleteRecord('pedidos_orcamento', row.id, true)
    rows.value = rows.value.filter((r) => r.id !== row.id)
    if (selected.value?.id === row.id) selected.value = null
    message.value = 'Orçamento eliminado.'
  } catch (e) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div class="split">
    <div class="list-pane">
      <h2>Orçamentos do site</h2>
      <p v-if="message" class="ok">{{ message }}</p>
      <p v-if="error" class="err">{{ error }}</p>
      <DataList
        :active-id="selected?.id"
        variant="conversation"
        :rows="rows"
        :columns="columns"
        :loading="loading"
        @open="openRow"
        @toggle-read="toggleRead"
        @delete="deleteRow"
      />
    </div>
    <OrderRecordPanel
      v-if="selected"
      kind="orcamento"
      :record="selected"
      @close="selected = null"
    />
    <div v-else class="placeholder card">
      <h3>Nenhum orçamento aberto</h3>
      <p>Escolha um orçamento na lista para ver os detalhes e descarregar o PDF.</p>
    </div>
  </div>
</template>

<style scoped>
.split { display: grid; grid-template-columns: minmax(280px, 1fr) minmax(320px, 1.2fr); gap: 20px; align-items: start; }
.list-pane h2 { margin: 0 0 12px; font-size: 1.1rem; }
.placeholder { padding: 24px; color: var(--text-muted); }
.placeholder h3 { margin: 0 0 8px; color: var(--text); }
.ok { color: var(--success); }
.err { color: var(--danger); }
@media (max-width: 900px) { .split { grid-template-columns: 1fr; } }
</style>
