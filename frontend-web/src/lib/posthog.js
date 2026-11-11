/** PostHog — só com consentimento (CookieBanner). SPA pageviews via router. */
let posthog = null // a biblioteca; o init faz-se uma só vez por página
let started = false
let client = null // = posthog enquanto há consentimento
let wanted = false // há consentimento agora: um carregamento em curso que já não é querido não chega a arrancar

export function isPosthogReady() {
  return Boolean(client)
}

/**
 * A biblioteca e a extensão dos web vitals (LCP, CLS, INP, FCP; PERF-06). O PostHog vai buscar a extensão a um script
 * externo, que `disable_external_dependency_loading` (e a CSP) impede: sem isto nunca houve um só `$web_vitals`. O pacote
 * `posthog-js/dist/web-vitals` regista-a no próprio PostHog e vai com a loja, no nosso domínio. Só se carrega depois do
 * consentimento, como o resto do PostHog.
 */
async function loadPosthog() {
  await import('posthog-js/dist/web-vitals')
  return (await import('posthog-js')).default
}

export async function initPosthog() {
  wanted = true
  const key = import.meta.env.VITE_POSTHOG_KEY || ''
  const host = import.meta.env.VITE_POSTHOG_HOST || 'https://eu.i.posthog.com'
  if (!key) return null

  posthog ??= await loadPosthog()
  if (!wanted) return null // o consentimento foi retirado enquanto a biblioteca carregava
  if (client) return client

  if (!started) {
    started = true
    posthog.init(key, {
      api_host: host,
      persistence: 'localStorage',
      autocapture: true,
      capture_pageview: false,
      capture_pageleave: true,
      // Tempos reais de carregamento (LCP, INP, CLS, FCP), só de quem aceitou: sem isto a loja não sabia como é para os
      // visitantes (PERF-06). A extensão vem de loadPosthog().
      capture_performance: { web_vitals: true },
      // A CSP só permite scripts do próprio domínio: sem isto o PostHog tentava
      // carregar surveys/config remotos de eu-assets.i.posthog.com e enchia a
      // consola de erros. Os eventos continuam a ser enviados normalmente.
      disable_external_dependency_loading: true,
      disable_surveys: true,
      // Retirar o consentimento tem de calar o PostHog de vez (LEGAL-07, RGPD art. 7.º/3). Por omissão ele
      // junta os eventos numa fila e envia-a de 3 em 3 s, mesmo depois do opt-out, e volta a pedir as
      // «feature flags» de tempos a tempos: um evento por pedido e sem flags (o site não usa nenhuma).
      request_batching: false,
      advanced_disable_flags: true,
      // No opt-out apaga as chaves ph_* que guardou e deixa de as escrever.
      opt_out_persistence_by_default: true,
    })
  }
  // Depois de uma retirada anterior (nesta página ou noutra visita) a marca de opt-out do PostHog fica guardada.
  if (posthog.has_opted_out_capturing()) posthog.opt_in_capturing({ captureEventName: false })
  client = posthog
  window.__diomikaPosthog = posthog
  capturePageview()
  return client
}

/**
 * Retirada (ou falta) de consentimento: pára já, apaga o que o PostHog guardou no dispositivo e deixa
 * `client` a null, para o pageview do router e `captureEvent` não fazerem nada. Pode chamar-se sem PostHog
 * ligado (consentimento expirado de uma visita anterior): então só apaga as chaves.
 */
export function stopPosthog() {
  wanted = false
  client?.opt_out_capturing()
  client = null
  delete window.__diomikaPosthog
  for (const area of ['localStorage', 'sessionStorage']) {
    try {
      const store = window[area]
      // Não as `__ph_opt_in_out_*`: sem essa marca um PostHog ainda vivo voltava a capturar.
      Object.keys(store)
        .filter((name) => name.startsWith('ph_'))
        .forEach((name) => store.removeItem(name))
    } catch {
      /* armazenamento bloqueado */
    }
  }
}

export function capturePageview() {
  if (!client) return
  client.capture('$pageview', {
    $current_url: window.location.href,
    $pathname: window.location.pathname,
  })
}

export function captureEvent(event, properties = {}) {
  if (!client) return
  client.capture(event, properties)
}
