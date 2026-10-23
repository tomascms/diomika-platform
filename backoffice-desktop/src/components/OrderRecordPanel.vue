<script setup>
import { ref } from 'vue'
import { api } from '@/lib/api'

const props = defineProps({
  kind: { type: String, required: true }, // 'orcamento' | 'encomenda'
  record: { type: Object, required: true },
  showBack: { type: Boolean, default: false },
})

defineEmits(['close', 'back'])

const error = ref('')
const loadingPdf = ref(false)

const title = () => {
  if (props.kind === 'orcamento') return `Orçamento — ${props.record.nome || '—'}`
  return `Encomenda — ${props.record.referencia_cliente || '—'}`
}

const meta = () => {
  if (props.kind === 'orcamento') {
    const parts = [
      props.record.email && `Email: ${props.record.email}`,
      props.record.contacto && `Contacto: ${props.record.contacto}`,
      props.record.empresa && `Empresa: ${props.record.empresa}`,
    ].filter(Boolean)
    return parts.join('\n') || 'Pedido do site.'
  }
  return `Criada: ${(props.record.created_at || '').slice(0, 10)}`
}

const lines = () => props.record.linhas || []

const downloadPdf = async () => {
  loadingPdf.value = true
  error.value = ''
  try {
    const blob =
      props.kind === 'orcamento'
        ? await api.orcamentoPdf(props.record.id)
        : await api.orderPdf(props.record.id)
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
  } catch (e) {
    error.value = e.message
  } finally {
    loadingPdf.value = false
  }
}
</script>

<template>
  <div class="detail card">
    <div class="head">
      <div>
        <button v-if="showBack" class="btn btn-ghost btn-sm" @click="$emit('back')">← Nova encomenda</button>
        <h3>{{ title() }}</h3>
      </div>
      <button class="btn btn-ghost btn-sm" @click="$emit('close')">×</button>
    </div>

    <p class="meta">{{ meta() }}</p>
    <p v-if="record.observacoes" class="obs"><strong>Obs:</strong> {{ record.observacoes }}</p>

    <h4>Linhas ({{ lines().length }})</h4>
    <ul v-if="lines().length" class="lines">
      <li v-for="(ln, i) in lines()" :key="i">
        {{ i + 1 }}. EAN {{ ln.ean }} · cor {{ ln.numero_cor }}
        <span v-if="ln.altura"> · {{ ln.altura }}</span>
        · qtd {{ ln.quantidade }}
      </li>
    </ul>
    <p v-else class="empty">Sem linhas registadas.</p>

    <p v-if="error" class="err">{{ error }}</p>
    <button class="btn btn-primary" :disabled="loadingPdf" @click="downloadPdf">
      {{ loadingPdf ? 'A gerar…' : 'Descarregar PDF' }}
    </button>
  </div>
</template>

<style scoped>
.detail { padding: 20px; }
.head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.head h3 { margin: 8px 0 0; }
.meta { white-space: pre-line; color: var(--text-muted); font-size: 0.9rem; }
.obs { font-size: 0.9rem; }
.lines { list-style: none; padding: 0; margin: 0 0 16px; }
.lines li { padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 0.92rem; }
.empty { color: var(--text-muted); }
.err { color: var(--danger); }
.btn-sm { padding: 4px 10px; font-size: 0.8rem; }
</style>
