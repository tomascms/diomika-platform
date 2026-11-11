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
  const isTestKey = configured === TEST_SITE_KEY || configured.startsWith('1x00000000000000000000')
  if (configured && !isTestKey) return configured
  if (import.meta.env.VITE_BETA_MODE === '1') return TEST_SITE_KEY
  return configured
}

const turnstileSiteKey = resolveTurnstileSiteKey()

// Para o visitante: o que aconteceu e o que fazer (FE-09). Nada de «autorize este hostname»: isso é para quem
// administra o Cloudflare, não para quem quer pedir um orçamento. Os formulários mostram WhatsApp e telefone ao lado.
const TURNSTILE_HELP =
  'Recarregue a página e tente de novo; se continuar, fale connosco por WhatsApp ou telefone.'
const TURNSTILE_LOAD_ERROR = `Não foi possível carregar a verificação anti-spam. ${TURNSTILE_HELP}`
const TURNSTILE_FAILED = `Não foi possível concluir a verificação anti-spam. ${TURNSTILE_HELP}`

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
        loadError.value = TURNSTILE_FAILED
      },
    })
  }

  const reset = () => {
    token.value = ''
    render()
  }

  // O Turnstile pesa ~1 MB (PERF-05): só carrega quando a pessoa toca no formulário, não a quem só quer o telefone ou o WhatsApp.
  let starting = null
  let started = false // o widget já foi desenhado
  const start = () => {
    if (!enabled) return Promise.resolve()
    starting ??= loadScript()
      .then(render)
      .catch(() => {
        loadError.value = TURNSTILE_LOAD_ERROR
      })
      .finally(() => {
        started = true
      })
    return starting
  }
  const onFormTouch = (e) => {
    const form = el.value?.closest('form')
    if (form && e.target instanceof Node && form.contains(e.target)) void start()
  }

  // Enviar antes de o widget acabar (preenchimento automático + Enter) espera por ele, em vez de falhar com «confirme».
  const requireToken = async () => {
    if (!enabled) return true
    if (!started) {
      await start()
      for (let i = 0; i < 50 && !token.value && !loadError.value; i++) {
        await new Promise((resolve) => setTimeout(resolve, 100))
      }
    }
    return Boolean(token.value)
  }

  onMounted(() => {
    if (!enabled) return
    document.addEventListener('focusin', onFormTouch)
    document.addEventListener('pointerdown', onFormTouch)
  })

  onUnmounted(() => {
    document.removeEventListener('focusin', onFormTouch)
    document.removeEventListener('pointerdown', onFormTouch)
    if (widgetId !== null && window.turnstile) {
      window.turnstile.remove(widgetId)
    }
  })

  return { enabled, token, el, loadError, render, reset, requireToken }
}
