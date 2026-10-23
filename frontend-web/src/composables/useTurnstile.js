import { ref, onMounted, onUnmounted } from 'vue'

const TEST_SITE_KEY = '1x00000000000000000000AA'

function isLocalHost() {
  if (typeof window === 'undefined') return false
  const h = window.location.hostname
  return h === 'localhost' || h === '127.0.0.1' || h === '[::1]'
}

function resolveTurnstileSiteKey() {
  // Em localhost a chave de produção falha (hostname não autorizado no widget CF).
  // Usa a sitekey de teste "always passes" só em desenvolvimento local.
  if (isLocalHost()) return TEST_SITE_KEY

  const configured = (import.meta.env.VITE_TURNSTILE_SITE_KEY || '').trim()
  const isTestKey =
    configured === TEST_SITE_KEY || configured.startsWith('1x00000000000000000000')
  if (configured && !isTestKey) return configured
  if (import.meta.env.VITE_BETA_MODE === '1') return TEST_SITE_KEY
  return configured
}

const turnstileSiteKey = resolveTurnstileSiteKey()

export function useTurnstile() {
  const enabled = Boolean(turnstileSiteKey)
  const token = ref('')
  const el = ref(null)
  const loadError = ref('')
  let widgetId = null

  const loadScript = () =>
    new Promise((resolve, reject) => {
      if (window.turnstile) {
        resolve()
        return
      }
      const existing = document.getElementById('cf-turnstile-script')
      if (existing) {
        existing.addEventListener('load', () => resolve())
        existing.addEventListener('error', reject)
        return
      }
      const script = document.createElement('script')
      script.id = 'cf-turnstile-script'
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
      script.async = true
      script.defer = true
      script.onload = () => resolve()
      script.onerror = reject
      document.head.appendChild(script)
    })

  const render = () => {
    if (!enabled || !el.value || !window.turnstile) return
    if (widgetId !== null) {
      window.turnstile.remove(widgetId)
    }
    widgetId = null
    loadError.value = ''
    widgetId = window.turnstile.render(el.value, {
      sitekey: turnstileSiteKey,
      theme: 'light',
      callback: (t) => {
        token.value = t
        loadError.value = ''
      },
      'expired-callback': () => {
        token.value = ''
      },
      'error-callback': () => {
        token.value = ''
        loadError.value = isLocalHost()
          ? 'Verificação anti-spam falhou em local. Recarregue a página.'
          : 'Verificação anti-spam indisponível neste domínio. No Cloudflare Turnstile, autorize este hostname (ex. www.diomika.com) e volte a tentar.'
      },
    })
  }

  const reset = () => {
    token.value = ''
    render()
  }

  const requireToken = () => {
    if (!enabled) return true
    return Boolean(token.value)
  }

  onMounted(async () => {
    if (!enabled) return
    try {
      await loadScript()
      render()
    } catch {
      loadError.value = 'Não foi possível carregar a verificação anti-spam.'
    }
  })

  onUnmounted(() => {
    if (widgetId !== null && window.turnstile) {
      window.turnstile.remove(widgetId)
    }
  })

  return { enabled, token, el, loadError, render, reset, requireToken }
}
