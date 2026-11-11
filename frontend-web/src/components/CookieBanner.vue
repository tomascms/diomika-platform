<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { initPosthog, stopPosthog } from '@/lib/posthog'
import { readConsent, saveConsent } from '@/lib/consent'
import { useCookieBanner } from '@/composables/useCookieBanner'

const posthogKey = import.meta.env.VITE_POSTHOG_KEY || ''

const { visible, reopened, close } = useCookieBanner()
const choice = ref(null) // a escolha em vigor: 'accepted', 'rejected' ou null (ainda não escolheu)
const dialog = ref(null)

const accept = async () => {
  choice.value = saveConsent('accepted')
  close()
  await initPosthog()
}

const reject = () => {
  choice.value = saveConsent('rejected')
  close()
  stopPosthog() // se já corria, pára já e apaga o que guardou: retirar é tão fácil como dar
}

// Reaberto pelo visitante: o foco passa para o diálogo. À primeira visita não se rouba o foco.
watch(
  dialog,
  (el) => {
    if (el && reopened.value) el.focus()
  },
  { flush: 'post' },
)

// Enquanto o banner está à vista a página ganha folga por baixo e `scroll-padding-bottom`, para o que tem foco nunca ficar
// tapado por ele (WCAG 2.4.11, A11Y-01). A altura muda com a largura do ecrã, por isso acompanha-se o elemento.
const root = document.documentElement
let observer = null
const syncHeight = () => {
  if (dialog.value)
    root.style.setProperty('--cookie-banner-h', `${dialog.value.offsetHeight + 32}px`)
}
const clearHeight = () => {
  observer?.disconnect()
  observer = null
  root.removeAttribute('data-cookie-banner')
  root.style.removeProperty('--cookie-banner-h')
}
watch(
  dialog,
  (el) => {
    clearHeight()
    if (!el) return
    root.setAttribute('data-cookie-banner', '')
    syncHeight()
    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver(syncHeight)
      observer.observe(el)
    }
  },
  { flush: 'post' },
)
onUnmounted(clearHeight)

onMounted(async () => {
  choice.value = readConsent()
  if (choice.value === 'accepted') {
    await initPosthog()
    return
  }
  // Sem consentimento em vigor (recusa, expirado ou de outra versão) não ficam identificadores do PostHog.
  stopPosthog()
  if (!choice.value && posthogKey) visible.value = true
})
</script>

<template>
  <Transition name="slide-up">
    <!-- `ph-no-capture`: o PostHog não regista cliques neste diálogo; escolher não se mede. -->
    <!-- Não é modal (não prende o foco nem tapa a página): uma região com nome, não um `role="dialog"` (A11Y-01). -->
    <section
      v-if="visible"
      ref="dialog"
      class="cookie-banner ph-no-capture"
      aria-label="Consentimento de cookies"
      tabindex="-1"
      @keydown.esc="reopened ? close() : reject()"
    >
      <p>
        Medimos as páginas e os cliques visitados, o que pesquisa e o tempo que as páginas demoram a
        abrir (PostHog, servidores na UE) para melhorar o site, só com o seu consentimento. Sem
        isso, o site funciona na mesma.
        <RouterLink to="/cookies">Cookies</RouterLink> ·
        <RouterLink to="/privacidade">Privacidade</RouterLink>.
        <strong v-if="reopened && choice" class="cookie-current">
          Escolha actual: {{ choice === 'accepted' ? 'aceitou' : 'recusou' }}. Pode mudá-la agora.
        </strong>
      </p>
      <div class="cookie-actions">
        <button v-if="reopened" type="button" class="btn btn-ghost btn-sm" @click="close">
          Fechar
        </button>
        <button type="button" class="btn btn-secondary btn-sm" @click="reject">Recusar</button>
        <button type="button" class="btn btn-primary btn-sm" @click="accept">Aceitar</button>
      </div>
    </section>
  </Transition>
</template>

<style scoped>
.cookie-banner {
  position: fixed;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2000;
  width: min(520px, calc(100% - 2rem));
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: 1rem 1.15rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1rem;
}

/* Recebe o foco por código ao reabrir; o diálogo já se destaca por si. */
.cookie-banner:focus {
  outline: none;
}

.cookie-banner p {
  margin: 0;
  flex: 1 1 220px;
  font-size: 0.9rem;
  color: var(--color-ink-soft);
  line-height: 1.45;
}

.cookie-banner p a {
  text-decoration: underline;
  text-underline-offset: 2px;
}

.cookie-current {
  display: block;
  margin-top: 0.4rem;
  color: var(--color-ink-deep);
}

.cookie-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-sm {
  padding: 0.45rem 0.85rem;
  font-size: 0.85rem;
}

@media (max-width: 520px) {
  /* No telemóvel tapava 18 % do ecrã (BR-07): mais compacto. */
  .cookie-banner {
    bottom: 0.5rem;
    width: calc(100% - 1rem);
    padding: 0.7rem 0.85rem;
    gap: 0.5rem 0.75rem;
  }

  .cookie-banner p {
    font-size: 0.82rem;
    line-height: 1.35;
  }
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition:
    opacity 0.25s ease,
    transform 0.25s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translate(-50%, 12px);
}
</style>
