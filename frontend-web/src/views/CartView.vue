<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useCart, resolveCartQtyRules, isValidCartQty } from '@/composables/useCart'
import { useTurnstile } from '@/composables/useTurnstile'
import { useInlineValidation } from '@/composables/useInlineValidation'
import { apiPost } from '@/lib/api'
import { captureEvent } from '@/lib/posthog'
import { MIN_ORCAMENTO_MSG, QUOTE_FORM_DRAFT_KEY, whatsappUrl } from '@/lib/constants'
import { nameError } from '@/lib/formRules'
import { nifError } from '@/lib/nif'
import { cartSummaryText, lineMeta, toQuoteLines } from '@/lib/quoteLines'
import { formKey } from '@/lib/idempotency'
import { localStore } from '@/lib/storage'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import ContactAlternatives from '@/components/ContactAlternatives.vue'
import StorageNotice from '@/components/StorageNotice.vue'
import QtyInput from '@/components/QtyInput.vue'
import SoftImage from '@/components/SoftImage.vue'
import { readOrigem } from '@/lib/origem'
import { readConsent } from '@/lib/consent'

const cart = useCart()
const turnstile = useTurnstile()
const {
  enabled: turnstileEnabled,
  el: turnstileEl,
  loadError: turnstileLoadError,
  token: turnstileToken,
  reset: resetTurnstile,
  requireToken,
} = turnstile
const items = ref([])
const submittedLines = ref([])
const submitting = ref(false)
const success = ref('')
const reference = ref('')
const error = ref('')
const needsHelp = ref(false) // o servidor não respondeu: oferece WhatsApp e telefone
// `tipo_cliente`: '' (não indicou), 'empresa' ou 'particular'. Nada vem pré-seleccionado.
const newForm = () => ({
  nome: '',
  email: '',
  contacto: '',
  tipo_cliente: '',
  empresa: '',
  nif: '',
  localidade: '',
  observacoes: '',
  website: '',
})
const form = ref(newForm())
const { formRef, errors, validate, clear, attrs, showSubmitError } = useInlineValidation({
  nome: nameError,
  nif: nifError,
})
const breadcrumbItems = [
  { label: 'Início', to: { name: 'home' } },
  { label: 'Pedido de orçamento' },
]
const reload = () => {
  items.value = cart.getItems()
}
const printQuote = () => window.print()

onMounted(() => {
  reload()
  try {
    // Só as observações ficam no dispositivo: nome, email e telefone são dados pessoais.
    const draft = JSON.parse(localStorage.getItem(QUOTE_FORM_DRAFT_KEY) || '{}')
    if (typeof draft.observacoes === 'string') form.value.observacoes = draft.observacoes
  } catch {
    /* rascunho inválido */
  }
})
watch(
  form,
  (value) => {
    if (success.value) return
    try {
      localStorage.setItem(
        QUOTE_FORM_DRAFT_KEY,
        JSON.stringify({ observacoes: value.observacoes || '' }),
      )
    } catch {
      /* storage indisponível */
    }
  },
  { deep: true },
)

const totalUnits = computed(() => items.value.reduce((n, i) => n + i.quantidade, 0))
const remove = (item) => {
  cart.removeItem(item.ean, item.numero_cor, item.altura || '')
  reload()
}
const changeQty = (item, qty) => {
  cart.updateQty(item.ean, item.numero_cor, Number(qty), item.altura || '')
  reload()
}
const cartRules = (item) => resolveCartQtyRules(item)
const quoteKey = formKey('diomika-orcamento-idempotency')

const orNull = (value) => value.trim() || null
const whatsappText = computed(() =>
  reference.value
    ? `Olá! Acabei de enviar o pedido de orçamento n.º ${reference.value} no site Diomika.`
    : 'Olá! Acabei de enviar um pedido de orçamento no site Diomika.',
)

const submit = async () => {
  error.value = ''
  success.value = ''
  reference.value = ''
  needsHelp.value = false
  if (form.value.website) return
  if (!items.value.length) {
    error.value = 'O pedido está vazio.'
    return
  }
  for (const item of items.value) {
    const { step, min } = cartRules(item)
    if (!isValidCartQty(item.quantidade, item)) {
      error.value = `Quantidade inválida para EAN ${item.ean}: mínimo ${min}, múltiplos de ${step}.`
      return
    }
  }
  if (!(await validate())) return
  if (!(await requireToken())) {
    error.value = 'Confirme a verificação anti-spam antes de enviar.'
    return
  }
  submitting.value = true
  try {
    const idempotencyKey = quoteKey.get()
    const f = form.value
    const response = await apiPost(
      '/orcamentos',
      {
        nome: f.nome.trim(),
        email: f.email.trim(),
        contacto: orNull(f.contacto),
        tipo_cliente: f.tipo_cliente || null,
        empresa: orNull(f.empresa),
        nif: orNull(f.nif),
        localidade: orNull(f.localidade),
        observacoes: orNull(f.observacoes),
        website: f.website,
        cf_turnstile_response: turnstileToken.value || null,
        linhas: toQuoteLines(items.value),
        origem: readOrigem(readConsent() === 'accepted'),
      },
      { idempotencyKey },
    )
    // Referência do pedido (RP-05): os 8 primeiros caracteres do id, os mesmos que o email para a equipa mostra («#id»).
    reference.value = String(response?.id ?? '').slice(0, 8)
    submittedLines.value = items.value.map((item) => ({ ...item }))
    success.value = 'Pedido enviado com sucesso.'
    captureEvent('quote_submitted', {
      reference: reference.value,
      items_count: items.value.length,
      total_units: totalUnits.value,
    })
    quoteKey.clear()
    localStore.remove(QUOTE_FORM_DRAFT_KEY)
    cart.clear()
    reload()
    form.value = newForm()
  } catch (e) {
    error.value = await showSubmitError(e, 'Erro ao enviar pedido.')
    needsHelp.value = Boolean(e.network || e.status >= 500)
    resetTurnstile()
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="cart-page">
    <Breadcrumbs :items="breadcrumbItems" />
    <div class="page-shell">
      <header class="page-header">
        <h1 class="page-title">Pedido de orçamento</h1>
        <p class="alert alert-info">{{ MIN_ORCAMENTO_MSG }}</p>
      </header>
      <StorageNotice v-if="items.length && !success" />
      <div v-if="items.length === 0 && !success" class="empty surface-card empty-card">
        <p>O seu pedido está vazio.</p>
        <RouterLink to="/categorias" class="btn btn-primary">Explorar catálogo</RouterLink>
      </div>
      <div v-else-if="!success" class="cart-layout">
        <section class="lines surface-card surface-card--elevated print-area">
          <div class="lines-head">
            <h2>Artigos</h2>
            <span class="badge-pill badge-soft">{{
              cartSummaryText({ lines: items.length, units: totalUnits })
            }}</span
            ><RouterLink to="/categorias" class="btn btn-secondary add-more-btn"
              >Adicionar mais artigos</RouterLink
            ><RouterLink to="/pedido-rapido" class="btn btn-secondary add-more-btn"
              >Pedido rápido por EAN</RouterLink
            ><button type="button" class="btn btn-secondary print-btn" @click="printQuote">
              Imprimir / PDF
            </button>
          </div>
          <article
            v-for="item in items"
            :key="`${item.ean}-${item.numero_cor}-${item.altura || ''}`"
            class="line"
          >
            <div v-if="item.imagem" class="line-thumb">
              <SoftImage :src="item.imagem" :alt="item.modeloNome" :thumb-width="160" thumb />
            </div>
            <div class="line-info">
              <strong>{{ item.modeloNome }}</strong
              ><span class="line-meta">{{ lineMeta(item) }}</span
              ><span class="line-ean">EAN {{ item.ean }}</span
              ><span class="line-qty-print">{{ item.quantidade }} un.</span>
            </div>
            <div class="line-actions">
              <QtyInput
                class="line-qty"
                :model-value="item.quantidade"
                :step="cartRules(item).step"
                :min="cartRules(item).min"
                :aria-label="`Quantidade de ${item.modeloNome}`"
                @update:model-value="changeQty(item, $event)"
              /><button type="button" class="btn btn-secondary remove-btn" @click="remove(item)">
                Remover
              </button>
            </div>
          </article>
        </section>
        <section class="form-section surface-card surface-card--elevated">
          <h2>Os seus dados</h2>
          <p class="form-hint">
            Os campos com * são obrigatórios.
          </p>
          <form
            ref="formRef"
            class="quote-form"
            novalidate
            @submit.prevent="submit"
            @input="clear($event.target.id)"
          >
            <input
              v-model="form.website"
              type="text"
              name="website"
              tabindex="-1"
              autocomplete="off"
              class="hp-field"
              aria-hidden="true"
            />
            <div>
              <label class="field-label" for="nome"
                >Nome <span class="req" aria-hidden="true">*</span></label
              >
              <input
                id="nome"
                v-model="form.nome"
                class="field-input"
                required
                minlength="2"
                maxlength="120"
                autocomplete="name"
                v-bind="attrs('nome')"
              />
              <p v-if="errors.nome" id="nome-erro" class="field-error">{{ errors.nome }}</p>
            </div>
            <div>
              <label class="field-label" for="email"
                >Email <span class="req" aria-hidden="true">*</span></label
              >
              <input
                id="email"
                v-model="form.email"
                class="field-input"
                type="email"
                required
                pattern="[^\s@]+@[^\s@]+\.[^\s@]+"
                autocomplete="email"
                data-erro="Indique um email válido, por exemplo nome@empresa.pt."
                v-bind="attrs('email')"
              />
              <p v-if="errors.email" id="email-erro" class="field-error">{{ errors.email }}</p>
            </div>
            <div>
              <label class="field-label" for="contacto"
                >Telefone <span class="field-optional">(opcional)</span></label
              >
              <input
                id="contacto"
                v-model="form.contacto"
                class="field-input"
                type="tel"
                inputmode="tel"
                maxlength="30"
                autocomplete="tel"
                v-bind="attrs('contacto')"
              />
              <p v-if="errors.contacto" id="contacto-erro" class="field-error">
                {{ errors.contacto }}
              </p>
            </div>
            <fieldset class="field-group">
              <legend class="field-label">
                Compro como <span class="field-optional">(opcional)</span>
              </legend>
              <div class="radio-options">
                <label class="radio-option"
                  ><input
                    v-model="form.tipo_cliente"
                    type="radio"
                    name="tipo_cliente"
                    value="empresa"
                  />
                  Empresa</label
                >
                <label class="radio-option"
                  ><input
                    v-model="form.tipo_cliente"
                    type="radio"
                    name="tipo_cliente"
                    value="particular"
                  />
                  Particular</label
                >
              </div>
            </fieldset>
            <div>
              <label class="field-label" for="empresa"
                >Empresa <span class="field-optional">(opcional)</span></label
              >
              <input
                id="empresa"
                v-model="form.empresa"
                class="field-input"
                maxlength="200"
                autocomplete="organization"
                v-bind="attrs('empresa')"
              />
              <p v-if="errors.empresa" id="empresa-erro" class="field-error">
                {{ errors.empresa }}
              </p>
            </div>
            <div>
              <label class="field-label" for="nif"
                >NIF <span class="field-optional">(opcional)</span></label
              >
              <input
                id="nif"
                v-model="form.nif"
                class="field-input"
                maxlength="20"
                autocomplete="off"
                spellcheck="false"
                placeholder="Número de contribuinte"
                v-bind="attrs('nif')"
              />
              <p v-if="errors.nif" id="nif-erro" class="field-error">{{ errors.nif }}</p>
            </div>
            <div>
              <label class="field-label" for="localidade"
                >Localidade <span class="field-optional">(opcional)</span></label
              >
              <input
                id="localidade"
                v-model="form.localidade"
                class="field-input"
                maxlength="120"
                autocomplete="address-level2"
                placeholder="Localidade (e país, se não for Portugal)"
                v-bind="attrs('localidade')"
              />
              <p v-if="errors.localidade" id="localidade-erro" class="field-error">
                {{ errors.localidade }}
              </p>
            </div>
            <div>
              <label class="field-label" for="observacoes"
                >Observações <span class="field-optional">(opcional)</span></label
              >
              <textarea
                id="observacoes"
                v-model="form.observacoes"
                class="field-textarea"
                maxlength="5000"
                placeholder="Prazos, entrega, notas sobre o projeto…"
                v-bind="attrs('observacoes')"
              />
              <p v-if="errors.observacoes" id="observacoes-erro" class="field-error">
                {{ errors.observacoes }}
              </p>
            </div>
            <div v-if="turnstileEnabled" ref="turnstileEl" class="turnstile-wrap" />
            <p v-if="turnstileLoadError" class="alert alert-error" role="alert">
              {{ turnstileLoadError }}
            </p>
            <p v-if="error" class="alert alert-error" role="alert">{{ error }}</p>
            <ContactAlternatives
              v-if="needsHelp || turnstileLoadError"
              whatsapp-text="Olá! Não consegui enviar o pedido de orçamento no site Diomika."
            />
            <!-- Aviso no momento da recolha (RGPD, art. 13.º) e pedido não vinculativo (DL 7/2004, art. 32.º): LEGAL-10. Novo separador, como a ligação às condições. -->
            <p class="form-hint">
              O pedido não é vinculativo: a venda só se conclui quando aceitar a nossa proposta.
              Usamos estes dados para lhe responder.
              <RouterLink to="/privacidade" target="_blank" rel="noopener"
                >Política de Privacidade</RouterLink
              >.
            </p>
            <button type="submit" class="btn btn-primary btn-block" :disabled="submitting">
              {{ submitting ? 'A enviar…' : 'Enviar pedido de orçamento' }}
            </button>
            <!-- Novo separador: no mesmo, o que já escreveu no formulário perdia-se (só as observações ficam guardadas). -->
            <p class="form-hint">
              Antes de aceitar a proposta, consulte as
              <RouterLink to="/condicoes-de-venda" target="_blank" rel="noopener"
                >Condições gerais de venda</RouterLink
              >
              (empresas e particulares).
            </p>
          </form>
        </section>
      </div>
      <section v-if="success" class="success-card surface-card" role="status">
        <h2>{{ success }}</h2>
        <p v-if="reference" class="quote-ref">
          Pedido n.º <strong class="quote-ref__id">{{ reference }}</strong>
        </p>
        <p v-if="reference">
          Guarde este número: indique-o se nos contactar por WhatsApp ou telefone.
        </p>
        <p>A nossa equipa responderá no prazo de 1 dia útil.</p>
        <div class="submitted-summary">
          <h3>Resumo enviado</h3>
          <p
            v-for="item in submittedLines"
            :key="`${item.ean}-${item.numero_cor}-${item.altura || ''}`"
          >
            <strong>{{ item.modeloNome }}</strong> — {{ item.quantidade }} un. · Cor
            {{ item.numero_cor }} · EAN {{ item.ean }}
          </p>
        </div>
        <div class="success-actions">
          <a
            class="btn btn-primary"
            :href="whatsappUrl(whatsappText)"
            target="_blank"
            rel="noopener noreferrer"
            >Falar no WhatsApp</a
          ><RouterLink to="/categorias" class="btn btn-secondary">Voltar ao catálogo</RouterLink>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.cart-page {
  padding-bottom: 2rem;
  background: var(--color-surface);
}
.page-header {
  margin-bottom: 1.5rem;
}
.page-header .alert {
  margin-top: 0.85rem;
  margin-bottom: 0;
}
.cart-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 1.25rem;
  align-items: start;
}
.lines,
.form-section {
  padding: 1.25rem 1.35rem;
}
.lines-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 0.5rem;
}
.lines-head h2,
.form-section h2 {
  margin: 0;
  font-size: 1.35rem;
}
.print-btn {
  margin-left: auto;
}
.add-more-btn {
  font-size: 0.88rem;
  padding: 0.45rem 0.85rem;
}
.line {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem 0;
  border-bottom: 1px solid var(--color-border);
}
.line:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.line-thumb {
  width: 72px;
  height: 72px;
  flex: 0 0 72px;
  overflow: hidden;
  border-radius: var(--radius-sm);
  background: var(--color-bg-soft);
}
.line-thumb :deep(.soft-image__img) {
  object-fit: cover;
}
.line-info {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}
.line-info strong {
  color: var(--color-ink);
}
.line-meta,
.line-ean {
  color: var(--color-muted);
  font-size: 0.9rem;
}
.line-ean {
  font-family: ui-monospace, monospace;
  font-size: 0.82rem;
}
.line-qty-print {
  display: none;
}
.line-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
  flex-shrink: 0;
}
.line-qty {
  min-width: 8rem;
}
.remove-btn {
  font-size: 0.88rem;
  padding: 0.45rem 0.85rem;
  color: var(--color-danger);
  border-color: var(--color-danger-soft);
}
.quote-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  position: relative;
}
.form-hint {
  font-size: 0.88rem;
  color: var(--color-muted);
}
.turnstile-wrap {
  min-height: 65px;
}
.hp-field {
  position: absolute;
  left: -9999px;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}
.empty-card,
.success-card {
  padding: 2.5rem;
  text-align: center;
}
.empty-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}
.success-card {
  max-width: 760px;
  margin: 0 auto;
}
.success-card h2 {
  color: var(--color-success);
}
.quote-ref {
  font-size: 1.15rem;
  margin: 0.5rem 0;
}
.quote-ref__id {
  font-family: ui-monospace, monospace;
  letter-spacing: 0.04em;
  user-select: all;
}
.submitted-summary {
  margin: 1.5rem auto;
  padding: 1rem;
  max-width: 620px;
  text-align: left;
  background: var(--color-bg-soft);
  border-radius: var(--radius-md);
}
.submitted-summary h3 {
  margin-top: 0;
}
.submitted-summary p {
  margin: 0.5rem 0;
}
.success-actions {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0.7rem;
}
.quote-form .form-hint {
  margin: 0;
}
/* minmax(0, …): com 1fr a coluna alargava ao conteúdo (o campo de quantidade e «Remover») e a página ganhava scroll horizontal. */
@media (max-width: 768px) {
  .cart-layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .line {
    flex-wrap: wrap;
  }
  .line-actions {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: flex-end;
  }
}
</style>
<style>
/* Só as linhas do pedido saem no papel. Este bloco não é «scoped» e o CSS desta vista carrega com a vista (e antes da
   visita, pelo pré-carregamento): as regras de antes escondiam `nav`, `footer` e `body *` em todas as páginas, e
   imprimir qualquer página dava uma folha em branco. Agora só valem quando o pedido está aberto (`body:has(.cart-page)`). */
@media print {
  body:has(.cart-page) :is(.app-header, .app-footer, .whatsapp-fab, .cookie-banner, .skip-link) {
    display: none !important;
  }
  .cart-page
    :is(
      .breadcrumbs,
      .page-header,
      .storage-notice,
      .form-section,
      .print-btn,
      .add-more-btn,
      .remove-btn,
      .line-qty
    ) {
    display: none !important;
  }
  .cart-page .print-area {
    box-shadow: none !important;
    border: 0 !important;
  }
  /* Os campos de quantidade não se imprimem: a quantidade de cada linha sai em texto. */
  .cart-page .line-qty-print {
    display: block !important;
    font-weight: 600;
  }
}
</style>
