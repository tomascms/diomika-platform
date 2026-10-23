<script setup>
import { ref, onMounted } from 'vue'
import { api } from '@/lib/api'
import DataList from '@/components/DataList.vue'
import ConversationPanel from '@/components/ConversationPanel.vue'

const rows = ref([])
const selected = ref(null)
const loading = ref(true)
const error = ref('')
const message = ref('')

const columns = [{ key: 'email', label: 'Email' }]

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    rows.value = await api.listContact()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const openMsg = async (row) => {
  selected.value = { ...row }
  message.value = ''
  if (!row.lida) {
    try {
      await api.markContactRead(row.id, true)
      row.lida = true
      selected.value = { ...row, lida: true }
    } catch (e) {
      error.value = e.message
    }
  }
}

const toggleRead = async (row) => {
  const next = !row.lida
  try {
    await api.markContactRead(row.id, next)
    row.lida = next
  } catch (e) {
    error.value = e.message
  }
}

const deleteMsg = async (row) => {
  if (
    !confirm(
      'Apagar esta mensagem da base de dados?\n\nEsta acção não pode ser desfeita.',
    )
  ) {
    return
  }
  try {
    await api.deleteRecord('contact_messages', row.id, true)
    rows.value = rows.value.filter((r) => r.id !== row.id)
    if (selected.value?.id === row.id) selected.value = null
    message.value = 'Mensagem eliminada.'
  } catch (e) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div class="contact-layout">
    <div class="list-pane">
      <h2>Mensagens de contacto</h2>
      <p class="hint">As respostas são enviadas a partir do seu programa de email.</p>
      <p v-if="message" class="ok">{{ message }}</p>
      <p v-if="error" class="err">{{ error }}</p>
      <DataList
        :active-id="selected?.id"
        variant="conversation"
        :rows="rows"
        :columns="columns"
        :loading="loading"
        @open="openMsg"
        @toggle-read="toggleRead"
        @delete="deleteMsg"
      />
    </div>
    <ConversationPanel :message="selected" />
  </div>
</template>

<style scoped>
.contact-layout {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(360px, 1.4fr);
  gap: 20px;
  align-items: start;
}
.list-pane h2 { margin: 0 0 6px; font-size: 1.1rem; }
.hint { margin: 0 0 12px; color: var(--text-muted); font-size: 0.88rem; }
.err { color: var(--danger); font-size: 0.9rem; }
.ok { color: var(--success); font-size: 0.9rem; }
@media (max-width: 900px) { .contact-layout { grid-template-columns: 1fr; } }
</style>
