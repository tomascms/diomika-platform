<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiPost } from '@/lib/api'
import { captureEvent } from '@/lib/posthog'
import { useTurnstile } from '@/composables/useTurnstile'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import { COMPANY, whatsappUrl } from '@/lib/constants'

const turnstile = useTurnstile()
const {
  enabled: turnstileEnabled,
  el: turnstileEl,
  loadError: turnstileLoadError,
  token: turnstileToken,
  reset: resetTurnstile,
  requireToken,
} = turnstile

const contactForm = ref({
  nome: '',
  email: '',
  contacto: '',
  assunto: '',
  mensagem: '',
  website: '',
})

const isSending = ref(false)
const messageSent = ref(false)
const errorMessage = ref('')

const breadcrumbItems = [
  { label: 'Início', to: { name: 'home' } },
  { label: 'Contacto' },
]

const IDEMPOTENCY_STORAGE_KEY = 'diomika-contact-idempotency'

const getOrCreateIdempotencyKey = () => {
  let key = sessionStorage.getItem(IDEMPOTENCY_STORAGE_KEY)
  if (!key) {
    key = crypto.randomUUID()
    sessionStorage.setItem(IDEMPOTENCY_STORAGE_KEY, key)
  }
  return key
}

const clearIdempotencyKey = () => {
  sessionStorage.removeItem(IDEMPOTENCY_STORAGE_KEY)
}

const submitContact = async () => {
  if (contactForm.value.website) return
  if (!requireToken()) {
    errorMessage.value = 'Confirme a verificação anti-spam antes de enviar.'
    return
  }

  isSending.value = true
  messageSent.value = false
  errorMessage.value = ''

  try {
    const idempotencyKey = getOrCreateIdempotencyKey()
    await apiPost('/contacto', {
      ...contactForm.value,
      cf_turnstile_response: turnstileToken.value || null,
    }, { idempotencyKey })
    messageSent.value = true
    captureEvent('contact_message_sent')
    clearIdempotencyKey()
    contactForm.value = { nome: '', email: '', contacto: '', assunto: '', mensagem: '', website: '' }
    resetTurnstile()
  } catch (e) {
    errorMessage.value = e.message || 'Erro ao enviar mensagem.'
    resetTurnstile()
  } finally {
    isSending.value = false
  }
}
</script>

<template>
  <div class="contact-page">
    <Breadcrumbs :items="breadcrumbItems" />

    <div class="page-shell contact-wrap">
      <h1 class="page-title">Contacto</h1>
      <div class="direct-actions">
        <a class="btn btn-secondary" :href="`tel:${COMPANY.phoneTel}`">Ligar {{ COMPANY.phoneDisplay }}</a>
        <a class="btn btn-primary" :href="whatsappUrl('Olá! Gostaria de falar com a Diomika.')" target="_blank" rel="noopener noreferrer">WhatsApp</a>
      </div>

      <p class="privacy-note">
        Usamos estes dados só para responder ao pedido.
        <RouterLink to="/privacidade">Privacidade</RouterLink>.
      </p>

      <form class="contact-form" @submit.prevent="submitContact">
        <input
          v-model="contactForm.website"
          type="text"
          name="website"
          tabindex="-1"
          autocomplete="off"
          class="hp-field"
          aria-hidden="true"
        />

        <div>
          <label class="field-label" for="nome">Nome</label>
          <input id="nome" v-model="contactForm.nome" class="field-input" placeholder="O seu nome" required maxlength="120" autocomplete="name" />
        </div>
        <div>
          <label class="field-label" for="email">Email</label>
          <input id="email" v-model="contactForm.email" class="field-input" type="email" placeholder="email@empresa.pt" required autocomplete="email" />
        </div>
        <div>
          <label class="field-label" for="contacto">Telefone</label>
          <input id="contacto" v-model="contactForm.contacto" class="field-input" type="tel" inputmode="tel" placeholder="912 345 678" required maxlength="20" autocomplete="tel" />
        </div>
        <div>
          <label class="field-label" for="assunto">Assunto</label>
          <input id="assunto" v-model="contactForm.assunto" class="field-input" placeholder="Motivo do contacto" required maxlength="200" />
        </div>
        <div>
          <label class="field-label" for="mensagem">Mensagem</label>
          <textarea id="mensagem" v-model="contactForm.mensagem" class="field-textarea" placeholder="Como podemos ajudar?" required rows="6" maxlength="5000" />
        </div>

        <div v-if="turnstileEnabled" ref="turnstileEl" class="turnstile-wrap" />
        <p v-if="turnstileLoadError" class="alert alert-error" role="alert">{{ turnstileLoadError }}</p>

        <button type="submit" class="btn btn-primary btn-block" :disabled="isSending" :aria-busy="isSending">
          {{ isSending ? 'A enviar…' : 'Enviar mensagem' }}
        </button>

        <p v-if="messageSent" class="alert alert-success" role="status">
          Mensagem enviada. Entraremos em contacto em breve.
        </p>
        <p v-if="errorMessage" class="alert alert-error" role="alert">{{ errorMessage }}</p>
      </form>
    </div>
  </div>
</template>

<style scoped>
.contact-page {
  padding-bottom: 2rem;
  background: #fff;
}

.contact-wrap {
  max-width: 640px;
  padding-top: 2rem;
}

.direct-actions { display: flex; flex-wrap: wrap; gap: 0.65rem; margin: 0.75rem 0 1.25rem; }

.privacy-note {
  font-size: 0.9rem;
  color: var(--color-muted);
  line-height: 1.5;
  margin: 0 0 1.25rem;
}

.contact-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  position: relative;
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
</style>
