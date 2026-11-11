/**
 * As rotas da loja, à parte do router para o pré-render (scripts/render-views.mjs) as poder ler em Node, sem
 * `createWebHistory`, e para o teste das páginas estáticas (scripts/static-pages.test.mjs) as ler também.
 */
export const routes = [
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
    path: '/pedido-rapido',
    name: 'quick-order',
    component: () => import('@/views/QuickOrderView.vue'),
  },
  {
    path: '/catalogo-imprimir',
    name: 'catalogue-print',
    component: () => import('@/views/CataloguePrintView.vue'),
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
    path: '/condicoes-de-venda',
    name: 'sales-terms',
    component: () => import('@/views/SalesTermsView.vue'),
  },
  {
    path: '/perguntas-frequentes',
    name: 'faq',
    component: () => import('@/views/FaqView.vue'),
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
    // Um endereço que não existe não entra nos motores de busca (usePageMeta.js).
    meta: { noindex: true },
  },
]
