import { createRouter, createWebHistory } from 'vue-router'
import { capturePageview, isPosthogReady } from '@/lib/posthog'
import { noteVisit } from '@/lib/origem'
import { readConsent } from '@/lib/consent'
import { consumeReloadMark, installStaleChunkRecovery } from '@/lib/staleChunk'
import { routes } from './routes'

/**
 * A página nova só monta depois de a rota (e os dados) carregarem: procurar a âncora logo a seguir à navegação
 * não a encontra e o scroll não acontece. Espera até ~1,5 s.
 */
function waitForAnchor(id) {
  return new Promise((resolve) => {
    let tries = 30
    const check = () => {
      if (document.getElementById(id)) resolve(true)
      else if (--tries <= 0) resolve(false)
      else setTimeout(check, 50)
    }
    check()
  })
}

// Se esta página abriu porque a anterior se recarregou sozinha (FE-12), a marca no endereço sai já, antes de o router o ler.
const reloadedAt = consumeReloadMark()

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to, _from, savedPosition) {
    if (to.hash) {
      return waitForAnchor(to.hash.slice(1)).then((found) =>
        found ? { el: to.hash, behavior: 'smooth', top: 80 } : { top: 0, behavior: 'instant' },
      )
    }
    if (savedPosition) return savedPosition
    // Instantâneo (FE-17): com o `scroll-behavior: smooth` do CSS a página demorava 1 a 2 s a chegar ao topo.
    return { top: 0, behavior: 'instant' }
  },
  routes,
})

// Separador aberto antes de um deploy: o ficheiro da página que se abre já não existe (FE-12).
installStaleChunkRecovery(router, { reloadedAt })

/** Pré-carrega chunks de rotas quentes (hover / idle). */
export function prefetchRoute(name) {
  try {
    const route = router.getRoutes().find((r) => r.name === name)
    const loaders = route?.components
      ? Object.values(route.components)
      : route?.component
        ? [route.component]
        : []
    for (const loader of loaders) {
      if (typeof loader === 'function') {
        const result = loader()
        if (result && typeof result.then === 'function') {
          result.catch(() => {})
        }
      }
    }
  } catch {
    /* ignore */
  }
}

function warmCatalogRoutes(currentName) {
  const warm = ['categories', 'products', 'product-detail', 'cart']
  for (const name of warm) {
    if (name !== currentName) prefetchRoute(name)
  }
}

router.afterEach((to) => {
  noteVisit({
    loc: window.location,
    referrer: document.referrer,
    routeName: to.name,
    params: to.params,
    allowed: readConsent() === 'accepted',
  })
  if (isPosthogReady()) capturePageview()
  const run = () => warmCatalogRoutes(to.name)
  if (typeof window !== 'undefined' && typeof window.requestIdleCallback === 'function') {
    window.requestIdleCallback(run, { timeout: 2500 })
  } else {
    setTimeout(run, 600)
  }
})

export default router
