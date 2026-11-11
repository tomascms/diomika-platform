import '@/assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { useRouteMeta } from '@/composables/usePageMeta'
import { QUOTE_FORM_DRAFT_KEY } from '@/lib/constants'

// Versões antigas guardavam nome/email/telefone do rascunho no browser: limpa em qualquer página.
try {
  const draft = JSON.parse(localStorage.getItem(QUOTE_FORM_DRAFT_KEY) || 'null')
  if (draft && (draft.nome || draft.email || draft.contacto)) {
    localStorage.setItem(
      QUOTE_FORM_DRAFT_KEY,
      JSON.stringify({ observacoes: draft.observacoes || '' }),
    )
  }
} catch {
  /* storage indisponível */
}

const app = createApp(App)
app.use(router)
useRouteMeta(router)
app.config.errorHandler = (err) => {
  console.error('[Diomika]', err)
}
// Bust stale module graph on custom domain after partial deploys.
if (typeof window !== 'undefined') window.__DIOMIKA_BUILD__ = '2026-10-03'
app.mount('#app')
