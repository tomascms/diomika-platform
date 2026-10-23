<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useCart, resolveCartQtyRules, isValidCartQty } from '@/composables/useCart'
import { useTurnstile } from '@/composables/useTurnstile'
import { apiPost } from '@/lib/api'
import { captureEvent } from '@/lib/posthog'
import { MIN_ORCAMENTO_MSG, QUOTE_FORM_DRAFT_KEY, whatsappUrl } from '@/lib/constants'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import QtySelect from '@/components/QtySelect.vue'
import SoftImage from '@/components/SoftImage.vue'

const cart = useCart()
const turnstile = useTurnstile()
const { enabled: turnstileEnabled, el: turnstileEl, loadError: turnstileLoadError, token: turnstileToken, reset: resetTurnstile, requireToken } = turnstile
const items = ref([])
const submittedLines = ref([])
const submitting = ref(false)
const success = ref('')
const error = ref('')
const form = ref({ nome: '', email: '', contacto: '', observacoes: '', website: '' })
const breadcrumbItems = [{ label: 'Início', to: { name: 'home' } }, { label: 'Pedido de orçamento' }]
const reload = () => { items.value = cart.getItems() }
const printQuote = () => window.print()

onMounted(() => {
  reload()
  try {
    // Só as observações ficam no dispositivo: nome, email e telefone são dados pessoais.
    const draft = JSON.parse(localStorage.getItem(QUOTE_FORM_DRAFT_KEY) || '{}')
    if (typeof draft.observacoes === 'string') form.value.observacoes = draft.observacoes
  } catch { /* rascunho inválido */ }
})
watch(form, (value) => {
  if (success.value) return
  try {
    localStorage.setItem(QUOTE_FORM_DRAFT_KEY, JSON.stringify({ observacoes: value.observacoes || '' }))
  } catch { /* storage indisponível */ }
}, { deep: true })

const totalUnits = computed(() => items.value.reduce((n, i) => n + i.quantidade, 0))
const remove = (item) => { cart.removeItem(item.ean, item.numero_cor, item.altura || ''); reload() }
const changeQty = (item, qty) => { cart.updateQty(item.ean, item.numero_cor, Number(qty), item.altura || ''); reload() }
const cartRules = (item) => resolveCartQtyRules(item)
const IDEMPOTENCY_STORAGE_KEY = 'diomika-orcamento-idempotency'
const getOrCreateIdempotencyKey = () => { let key = sessionStorage.getItem(IDEMPOTENCY_STORAGE_KEY); if (!key) { key = crypto.randomUUID(); sessionStorage.setItem(IDEMPOTENCY_STORAGE_KEY, key) } return key }
const clearIdempotencyKey = () => sessionStorage.removeItem(IDEMPOTENCY_STORAGE_KEY)

const submit = async () => {
  error.value = ''; success.value = ''
  if (form.value.website) return
  if (!items.value.length) { error.value = 'O pedido está vazio.'; return }
  for (const item of items.value) {
    const { step, min } = cartRules(item)
    if (!isValidCartQty(item.quantidade, item)) { error.value = `Quantidade inválida para EAN ${item.ean}: mínimo ${min}, múltiplos de ${step}.`; return }
  }
  if (!requireToken()) { error.value = 'Confirme a verificação anti-spam antes de enviar.'; return }
  submitting.value = true
  try {
    const idempotencyKey = getOrCreateIdempotencyKey()
    const contacto = form.value.contacto.trim()
    const observacoes = form.value.observacoes.trim()
    await apiPost('/orcamentos', {
      nome: form.value.nome.trim(), email: form.value.email.trim(), contacto: contacto || null, observacoes: observacoes || null,
      website: form.value.website, cf_turnstile_response: turnstileToken.value || null,
      linhas: items.value.map((i) => ({ ean: i.ean, numero_cor: Number(i.numero_cor), quantidade: Number(i.quantidade), ...(i.altura ? { altura: i.altura } : {}) })),
    }, { idempotencyKey })
    submittedLines.value = items.value.map((item) => ({ ...item }))
    success.value = 'Pedido enviado com sucesso.'
    captureEvent('quote_submitted', { items_count: items.value.length, total_units: totalUnits.value })
    clearIdempotencyKey(); localStorage.removeItem(QUOTE_FORM_DRAFT_KEY); cart.clear(); reload()
    form.value = { nome: '', email: '', contacto: '', observacoes: '', website: '' }
  } catch (e) { error.value = e.message || 'Erro ao enviar pedido.'; resetTurnstile() }
  finally { submitting.value = false }
}
</script>

<template>
  <div class="cart-page">
    <Breadcrumbs :items="breadcrumbItems" />
    <div class="page-shell">
      <header class="page-header"><h1 class="page-title">Pedido de orçamento</h1><p class="alert alert-info">{{ MIN_ORCAMENTO_MSG }}</p></header>
      <div v-if="items.length === 0 && !success" class="empty surface-card empty-card"><p>O seu pedido está vazio.</p><RouterLink to="/categorias" class="btn btn-primary">Explorar catálogo</RouterLink></div>
      <div v-else-if="!success" class="cart-layout">
        <section class="lines surface-card surface-card--elevated print-area">
          <div class="lines-head"><h2>Artigos</h2><span class="badge-pill badge-soft">{{ totalUnits }} un.</span><button type="button" class="btn btn-secondary print-btn" @click="printQuote">Imprimir / PDF</button></div>
          <article v-for="item in items" :key="`${item.ean}-${item.numero_cor}-${item.altura || ''}`" class="line">
            <div v-if="item.imagem" class="line-thumb"><SoftImage :src="item.imagem" :alt="item.modeloNome" thumb /></div>
            <div class="line-info"><strong>{{ item.modeloNome }}</strong><span class="line-meta">{{ item.dimensoes }}{{ item.altura ? '' : ' cm' }} · Cor {{ item.numero_cor }}{{ item.corNome ? ` (${item.corNome})` : '' }}</span><span class="line-ean">EAN {{ item.ean }}</span></div>
            <div class="line-actions"><label class="qty-field"><span class="field-label">Quantidade</span><QtySelect :model-value="item.quantidade" :step="cartRules(item).step" :min="cartRules(item).min" unit-label="un." @update:model-value="changeQty(item, $event)" /></label><button type="button" class="btn btn-secondary remove-btn" @click="remove(item)">Remover</button></div>
          </article>
        </section>
        <section class="form-section surface-card surface-card--elevated"><h2>Os seus dados</h2><p class="form-hint">Nome e email são obrigatórios. Os seus dados não ficam guardados neste dispositivo.</p>
          <form class="quote-form" @submit.prevent="submit">
            <input v-model="form.website" type="text" name="website" tabindex="-1" autocomplete="off" class="hp-field" aria-hidden="true" />
            <div><label class="field-label" for="nome">Nome *</label><input id="nome" v-model="form.nome" class="field-input" required autocomplete="name" /></div>
            <div><label class="field-label" for="email">Email *</label><input id="email" v-model="form.email" class="field-input" type="email" required autocomplete="email" /></div>
            <div><label class="field-label" for="contacto">Contacto</label><input id="contacto" v-model="form.contacto" class="field-input" type="tel" inputmode="tel" autocomplete="tel" placeholder="Telefone (opcional)" /></div>
            <div><label class="field-label" for="observacoes">Observações</label><textarea id="observacoes" v-model="form.observacoes" class="field-textarea" placeholder="Prazos, entrega, notas sobre o projecto…" /></div>
            <div v-if="turnstileEnabled" ref="turnstileEl" class="turnstile-wrap" /><p v-if="turnstileLoadError" class="alert alert-error" role="alert">{{ turnstileLoadError }}</p><p v-if="error" class="alert alert-error" role="alert">{{ error }}</p>
            <button type="submit" class="btn btn-primary btn-block" :disabled="submitting">{{ submitting ? 'A enviar…' : 'Enviar pedido de orçamento' }}</button>
          </form>
        </section>
      </div>
      <section v-if="success" class="success-card surface-card" role="status"><h2>{{ success }}</h2><p>A nossa equipa responderá no prazo de 1 dia útil.</p><div class="submitted-summary"><h3>Resumo enviado</h3><p v-for="item in submittedLines" :key="`${item.ean}-${item.numero_cor}-${item.altura || ''}`"><strong>{{ item.modeloNome }}</strong> — {{ item.quantidade }} un. · Cor {{ item.numero_cor }} · EAN {{ item.ean }}</p></div><div class="success-actions"><a class="btn btn-primary" :href="whatsappUrl('Olá! Acabei de enviar um pedido de orçamento no site Diomika.')" target="_blank" rel="noopener noreferrer">Falar no WhatsApp</a><RouterLink to="/categorias" class="btn btn-secondary">Voltar ao catálogo</RouterLink></div></section>
    </div>
  </div>
</template>

<style scoped>
.cart-page { padding-bottom: 2rem; background: #fff; }
.page-header { margin-bottom: 1.5rem; }.page-header .alert { margin-top: 0.85rem; margin-bottom: 0; }
.cart-layout { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 1.25rem; align-items: start; }
.lines, .form-section { padding: 1.25rem 1.35rem; }
.lines-head { display: flex; align-items: center; gap: 0.65rem; margin-bottom: 0.5rem; }.lines-head h2, .form-section h2 { margin: 0; font-size: 1.35rem; }.print-btn { margin-left: auto; }
.line { display: flex; align-items: flex-start; gap: 1rem; padding: 1rem 0; border-bottom: 1px solid var(--color-border); }.line:last-child { border-bottom: none; padding-bottom: 0; }
.line-thumb { width: 72px; height: 72px; flex: 0 0 72px; overflow: hidden; border-radius: var(--radius-sm); background: var(--color-bg-soft); }.line-thumb :deep(.soft-image__img) { object-fit: cover; }
.line-info { display: flex; flex: 1; flex-direction: column; gap: 0.25rem; min-width: 0; }.line-info strong { color: var(--color-ink); }.line-meta, .line-ean { color: var(--color-muted); font-size: 0.9rem; }.line-ean { font-family: ui-monospace, monospace; font-size: 0.82rem; }
.line-actions { display: flex; flex-direction: column; align-items: flex-end; gap: 0.5rem; flex-shrink: 0; }.qty-field { min-width: 8rem; }.remove-btn { font-size: 0.88rem; padding: 0.45rem 0.85rem; color: var(--color-danger); border-color: var(--color-danger-soft); }
.quote-form { display: flex; flex-direction: column; gap: 1rem; position: relative; }.form-hint { font-size: 0.88rem; color: var(--color-muted); }.turnstile-wrap { min-height: 65px; }.hp-field { position: absolute; left: -9999px; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
.empty-card, .success-card { padding: 2.5rem; text-align: center; }.empty-card { display: flex; flex-direction: column; align-items: center; gap: 1rem; }.success-card { max-width: 760px; margin: 0 auto; }.success-card h2 { color: var(--color-success); }.submitted-summary { margin: 1.5rem auto; padding: 1rem; max-width: 620px; text-align: left; background: var(--color-bg-soft); border-radius: var(--radius-md); }.submitted-summary h3 { margin-top: 0; }.submitted-summary p { margin: 0.5rem 0; }.success-actions { display: flex; justify-content: center; flex-wrap: wrap; gap: 0.7rem; }
@media (max-width: 768px) { .cart-layout { grid-template-columns: 1fr; }.line { flex-wrap: wrap; }.line-actions { width: 100%; flex-direction: row; justify-content: space-between; align-items: flex-end; } }
</style>
<style>
@media print {
  nav, footer, .whatsapp-fab, .form-section, .print-btn { display: none !important; }
  body * { visibility: hidden !important; }
  .print-area, .print-area * { visibility: visible !important; }
  .print-area { position: absolute !important; inset: 0 auto auto 0; width: 100%; box-shadow: none !important; border: 0 !important; }
  .print-area .print-btn, .print-area .remove-btn, .print-area .qty-field { display: none !important; }
}
</style>
