import { createRouter, createWebHistory } from 'vue-router'
import { capturePageview, isPosthogReady } from '@/lib/posthog'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to, _from, savedPosition) {
    if (to.hash) {
      return {
        el: to.hash,
        behavior: 'smooth',
        top: 80,
      }
    }
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/categorias',
      name: 'categories',
      component: () => import('@/views/CategoriesView.vue'),
    },
    {
      path: '/categoria/:categorySlug',
      name: 'products',
      component: () => import('@/views/ProductsView.vue'),
    },
    {
      path: '/categoria/:categorySlug/:modelSlug',
      name: 'product-detail',
      component: () => import('@/views/ProductDetailView.vue'),
    },
    {
      path: '/produtos/:categorySlug',
      redirect: (to) => ({
        name: 'products',
        params: { categorySlug: to.params.categorySlug },
      }),
    },
    {
      path: '/produto/:legacyModelId',
      name: 'product-detail-legacy',
      component: () => import('@/views/ProductDetailView.vue'),
    },
    {
      path: '/pesquisa',
      name: 'search',
      component: () => import('@/views/SearchView.vue'),
    },
    {
      path: '/carrinho',
      name: 'cart',
      component: () => import('@/views/CartView.vue'),
    },
    {
      path: '/contacto',
      name: 'contact',
      component: () => import('@/views/ContactView.vue'),
      alias: ['/contact'],
    },
    {
      path: '/sobre',
      name: 'about',
      component: () => import('@/views/AboutView.vue'),
    },
    {
      path: '/privacidade',
      name: 'privacy',
      component: () => import('@/views/PrivacyView.vue'),
    },
    {
      path: '/termos',
      name: 'terms',
      component: () => import('@/views/TermsView.vue'),
    },
    {
      path: '/cookies',
      name: 'cookies',
      component: () => import('@/views/CookiesView.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
    },
  ],
})

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
  if (isPosthogReady()) capturePageview()
  const run = () => warmCatalogRoutes(to.name)
  if (typeof window !== 'undefined' && typeof window.requestIdleCallback === 'function') {
    window.requestIdleCallback(run, { timeout: 2500 })
  } else {
    setTimeout(run, 600)
  }
})

export default router
