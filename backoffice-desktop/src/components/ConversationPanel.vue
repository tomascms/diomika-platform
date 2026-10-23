<script setup>
import { ref, watch } from 'vue'
import { api } from '@/lib/api'

const props = defineProps({
  message: { type: Object, default: null },
})

const history = ref([])
const loadingHistory = ref(false)
const error = ref('')

const lastSenderLabel = (value) => {
  if (value === 'vendor') return 'Loja (tu)'
  if (value === 'client') return 'Cliente'
  return '—'
}

const formatDate = (value) => {
  if (!value) return ''
  try {
    return new Date(value).toLocaleString('pt-PT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return String(value).slice(0, 16)
  }
}

const loadHistory = async () => {
  history.value = []
  error.value = ''
  if (!props.message?.id) return

  loadingHistory.value = true
  try {
    const data = await api.getContactMessage(props.message.id)
    history.value = data.history || []
  } catch (e) {
    error.value = e.message
  } finally {
    loadingHistory.value = false
  }
}

watch(() => props.message?.id, loadHistory, { immediate: true })
</script>

<template>
  <div v-if="!message" class="placeholder card">
    <h3>Nenhuma mensagem aberta</h3>
    <p>Escolha uma mensagem na lista para ver a conversa completa.</p>
  </div>

  <div v-else class="conversation card">
    <div class="meta">
      <div class="chips">
        <span class="chip">{{ message.status || 'Nova' }}</span>
        <span class="chip muted">Último: {{ lastSenderLabel(message.last_sender) }}</span>
      </div>
      <button type="button" class="btn btn-ghost btn-sm" :disabled="loadingHistory" @click="loadHistory">
        {{ loadingHistory ? 'A actualizar…' : '↻ Actualizar' }}
      </button>
    </div>

    <p class="who">{{ message.nome }} &lt;{{ message.email }}&gt;</p>
    <h3>{{ message.assunto || '(sem assunto)' }}</h3>

    <div class="thread">
      <article class="bubble client">
        <p class="head">Cliente · {{ formatDate(message.created_at) }}</p>
        <p v-if="message.contacto" class="sub">Tel: {{ message.contacto }}</p>
        <p class="body">{{ message.mensagem }}</p>
      </article>

      <p v-if="loadingHistory && !history.length" class="loading-hint">A carregar respostas…</p>

      <article
        v-for="reply in history"
        :key="reply.id"
        class="bubble"
        :class="reply.role === 'vendor' ? 'vendor' : 'client'"
      >
        <p class="head">
          {{ reply.role === 'vendor' ? 'Loja' : 'Cliente' }} · {{ formatDate(reply.created_at) }}
        </p>
        <p class="body">{{ reply.body || '(sem texto)' }}</p>
      </article>
    </div>

    <p v-if="error" class="err">Histórico indisponível: {{ error }}</p>
  </div>
</template>

<style scoped>
.placeholder { padding: 24px; color: var(--text-muted); }
.placeholder h3 { margin: 0 0 8px; color: var(--text); }
.conversation { padding: 20px; display: grid; gap: 12px; }
.meta { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip { background: var(--bg-elevated); border-radius: 999px; padding: 4px 10px; font-size: 0.78rem; font-weight: 600; }
.chip.muted { color: var(--text-muted); font-weight: 500; }
.who { margin: 0; color: var(--text-muted); font-size: 0.9rem; }
.conversation h3 { margin: 0; font-size: 1.05rem; }
.thread { display: grid; gap: 10px; max-height: 60vh; overflow: auto; padding-right: 4px; }
.bubble { border-radius: 14px; padding: 12px 14px; background: var(--bg-elevated); }
.bubble.vendor { margin-left: 48px; background: rgba(108, 140, 255, 0.12); }
.bubble.client { margin-right: 48px; }
.head { margin: 0 0 6px; font-size: 0.78rem; color: var(--text-muted); }
.sub { margin: 0 0 6px; font-size: 0.82rem; color: var(--text-muted); }
.body { margin: 0; white-space: pre-wrap; line-height: 1.45; }
.loading-hint { margin: 0; color: var(--text-muted); font-size: 0.88rem; }
.err { color: var(--danger); margin: 0; font-size: 0.88rem; }
.btn-sm { padding: 4px 10px; font-size: 0.8rem; }
</style>
