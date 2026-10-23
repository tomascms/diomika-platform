/* Archivo variável (pesos + eixo de largura) servida localmente: a CSP só
   permite fontes do próprio domínio e um único ficheiro cobre texto e títulos
   expandidos. O browser só descarrega o subconjunto latin que a página usa. */
import '@fontsource-variable/archivo/wdth.css'
import '@/assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { useRouteMeta } from '@/composables/usePageMeta'
import { injectOrganizationJsonLd } from '@/composables/useStructuredData'
import { QUOTE_FORM_DRAFT_KEY } from '@/lib/constants'

// Versões antigas guardavam nome/email/telefone do rascunho no browser: limpa em qualquer página.
try {
  const draft = JSON.parse(localStorage.getItem(QUOTE_FORM_DRAFT_KEY) || 'null')
  if (draft && (draft.nome || draft.email || draft.contacto)) {
    localStorage.setItem(QUOTE_FORM_DRAFT_KEY, JSON.stringify({ observacoes: draft.observacoes || '' }))
  }
} catch { /* storage indisponível */ }

const app = createApp(App)
app.use(router)
useRouteMeta(router)
injectOrganizationJsonLd()
app.config.errorHandler = (err) => {
  console.error('[Diomika]', err)
}
// Bust stale module graph on custom domain after partial deploys.
if (typeof window !== 'undefined') window.__DIOMIKA_BUILD__ = '2026-10-03'
app.mount('#app')
