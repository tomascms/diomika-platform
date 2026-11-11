<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { api } from '@/lib/api'
import {
  QUOTE_STATUSES,
  REPLY_TEMPLATES,
  lineText,
  mailtoUrl,
  managementChanges,
  origemLines,
} from '@/lib/quote'

const props = defineProps({
  kind: { type: String, required: true }, // 'orcamento' | 'encomenda'
  record: { type: Object, required: true },
  showBack: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'back', 'managed'])

const error = ref('')
const loadingPdf = ref(false)

const title = () => {
  if (props.kind === 'orcamento') return `Orçamento — ${props.record.nome || '—'}`
  return `Encomenda — ${props.record.referencia_cliente || '—'}`
}

const TIPO_CLIENTE = { empresa: 'Empresa', particular: 'Particular' }

const meta = () => {
  if (props.kind === 'orcamento') {
    const r = props.record
    const parts = [
      // A referência que o comprador vê no ecrã e no recibo (e que o email para a equipa mostra como «#id»).
      r.id && `Pedido n.º ${String(r.id).slice(0, 8)}`,
      r.email && `Email: ${r.email}`,
      r.contacto && `Contacto: ${r.contacto}`,
      r.tipo_cliente && `Compra como: ${TIPO_CLIENTE[r.tipo_cliente] || r.tipo_cliente}`,
      r.empresa && `Empresa: ${r.empresa}`,
      r.nif && `NIF: ${r.nif}`,
      r.localidade && `Localidade: ${r.localidade}`,
    ].filter(Boolean)
    return parts.join('\n') || 'Pedido do site.'
  }
  return `Criada: ${(props.record.created_at || '').slice(0, 10)}`
}

const lines = () => props.record.linhas_detalhe || props.record.linhas || []

const isQuote = computed(() => props.kind === 'orcamento')
const origem = computed(() => origemLines(props.record.origem))
const soldOn = computed(() => (props.record.vendido_em ? String(props.record.vendido_em).slice(0, 10) : ''))

// Estado, valor da proposta e nota interna (RP-06). Repõe-se ao abrir outro orçamento.
const form = reactive({ status: 'Nova', valor_proposta: '', nota_interna: '' })
const managing = ref(false)
const manageMessage = ref('')
watch(
  () => props.record.id,
  () => {
    form.status = props.record.status || 'Nova'
    form.valor_proposta = props.record.valor_proposta == null ? '' : String(props.record.valor_proposta)
    form.nota_interna = props.record.nota_interna || ''
    manageMessage.value = ''
  },
  { immediate: true },
)
const changes = computed(() => managementChanges(props.record, form))
const hasChanges = computed(() => Object.keys(changes.value).length > 0)

const saveManagement = async () => {
  managing.value = true
  error.value = ''
  manageMessage.value = ''
  try {
    const updated = await api.quoteManagement(props.record.id, changes.value)
    emit('managed', updated)
    manageMessage.value = 'Guardado.'
  } catch (e) {
    error.value = e.message
  } finally {
    managing.value = false
  }
}

// «Responder por email»: abre o programa de email com o modelo escolhido (o backoffice não envia emails).
const templateId = ref(REPLY_TEMPLATES[0].id)
const currentTemplate = () => REPLY_TEMPLATES.find((t) => t.id === templateId.value).build(props.record)
const replyHref = computed(() => mailtoUrl(props.record.email, currentTemplate()))
const copied = ref(false)
const copyTemplate = async () => {
  try {
    await navigator.clipboard.writeText(currentTemplate().body)
    copied.value = true
    setTimeout(() => (copied.value = false), 2500)
  } catch {
    error.value = 'Não foi possível copiar o texto.'
  }
}

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
    <p v-if="isQuote && origem.length" class="origem">{{ origem.join(' · ') }}</p>

    <section v-if="isQuote" class="manage">
      <h4>Ciclo do pedido</h4>
      <div class="manage-grid">
        <label>
          <span>Estado</span>
          <select v-model="form.status" class="input">
            <option v-for="s in QUOTE_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </label>
        <label>
          <span>Valor da proposta (€)</span>
          <input v-model="form.valor_proposta" class="input" inputmode="decimal" placeholder="ex.: 615,00" />
        </label>
      </div>
      <label class="note">
        <span>Nota interna (o cliente não vê)</span>
        <textarea v-model="form.nota_interna" class="input" rows="3" maxlength="2000" />
      </label>
      <p v-if="soldOn" class="sold">Vendido em {{ soldOn }}: este pedido não é apagado pela retenção de 24 meses.</p>
      <div class="manage-actions">
        <button class="btn btn-primary btn-sm" :disabled="managing || !hasChanges" @click="saveManagement">
          {{ managing ? 'A guardar…' : 'Guardar' }}
        </button>
        <span v-if="manageMessage" class="ok">{{ manageMessage }}</span>
      </div>
    </section>

    <h4>Linhas ({{ lines().length }})</h4>
    <ul v-if="lines().length" class="lines">
      <li v-for="(ln, i) in lines()" :key="i">
        {{ i + 1 }}. {{ lineText(ln) }}
        <span v-if="ln.modelo && ln.modelo !== '?'" class="ean">EAN {{ ln.ean }}</span>
      </li>
    </ul>
    <p v-else class="empty">Sem linhas registadas.</p>

    <p v-if="error" class="err">{{ error }}</p>
    <button class="btn btn-primary" :disabled="loadingPdf" @click="downloadPdf">
      {{ loadingPdf ? 'A gerar…' : 'Descarregar PDF' }}
    </button>

    <section v-if="isQuote && record.email" class="reply">
      <h4>Responder por email</h4>
      <p class="hint">
        Preencha o que está entre [parênteses] e anexe o PDF.
      </p>
      <div class="reply-row">
        <select v-model="templateId" class="input" aria-label="Modelo de resposta">
          <option v-for="t in REPLY_TEMPLATES" :key="t.id" :value="t.id">{{ t.label }}</option>
        </select>
        <a class="btn btn-primary btn-sm" :href="replyHref">Abrir no email</a>
        <button type="button" class="btn btn-ghost btn-sm" @click="copyTemplate">
          {{ copied ? 'Copiado' : 'Copiar texto' }}
        </button>
      </div>
    </section>
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
.origem { font-size: 0.85rem; color: var(--text-muted); }
.ean { color: var(--text-muted); font-size: 0.8rem; margin-left: 6px; }
.manage, .reply { margin: 16px 0; padding-top: 12px; border-top: 1px solid var(--border); display: grid; gap: 10px; }
.manage h4, .reply h4 { margin: 0; }
.manage-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.manage label, .note { display: grid; gap: 4px; font-size: 0.85rem; color: var(--text-muted); }
.manage-actions, .reply-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.sold { margin: 0; font-size: 0.85rem; color: var(--success); }
.ok { color: var(--success); font-size: 0.85rem; }
.hint { margin: 0; font-size: 0.85rem; color: var(--text-muted); }
</style>
