<script setup>
import { ref, onMounted } from 'vue'
import { initPosthog } from '@/lib/posthog'

const CONSENT_KEY = 'diomika_cookie_consent'
const posthogKey = import.meta.env.VITE_POSTHOG_KEY || ''

const visible = ref(false)

const accept = async () => {
  localStorage.setItem(CONSENT_KEY, 'accepted')
  visible.value = false
  await initPosthog()
}

const reject = () => {
  localStorage.setItem(CONSENT_KEY, 'rejected')
  visible.value = false
}

onMounted(async () => {
  const saved = localStorage.getItem(CONSENT_KEY)
  if (saved === 'accepted') {
    await initPosthog()
    return
  }
  if (saved === 'rejected') return
  if (!posthogKey) return
  visible.value = true
})
</script>

<template>
  <Transition name="slide-up">
    <aside v-if="visible" class="cookie-banner" role="dialog" aria-label="Consentimento de cookies">
      <p>
        Utilizamos analytics (PostHog) para melhorar o site — só com o seu consentimento.
        <RouterLink to="/cookies">Cookies</RouterLink> ·
        <RouterLink to="/privacidade">Privacidade</RouterLink>.
      </p>
      <div class="cookie-actions">
        <button type="button" class="btn btn-secondary btn-sm" @click="reject">Recusar</button>
        <button type="button" class="btn btn-primary btn-sm" @click="accept">Aceitar</button>
      </div>
    </aside>
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

.cookie-banner p {
  margin: 0;
  flex: 1 1 220px;
  font-size: 0.9rem;
  color: var(--color-ink-soft);
  line-height: 1.45;
}

.cookie-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-sm {
  padding: 0.45rem 0.85rem;
  font-size: 0.85rem;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translate(-50%, 12px);
}
</style>
