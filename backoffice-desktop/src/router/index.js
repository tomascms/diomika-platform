import { createRouter, createWebHashHistory } from 'vue-router'
import { bootstrapSettings, isAuthenticated } from '@/lib/settings'
import { loadWorkspace, workspace } from '@/composables/useWorkspace'
import { UNAUTHORIZED_EVENT } from '@/lib/api'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/AppShell.vue'),
      children: [
        { path: '', redirect: { name: 'workspace', params: { table: 'categories' } } },
        {
          path: 'workspace/:table',
          name: 'workspace',
          component: () => import('@/views/WorkspaceRouter.vue'),
        },
        {
          path: 'workspace/:table/new',
          name: 'record-new',
          component: () => import('@/views/RecordFormView.vue'),
        },
        {
          path: 'workspace/:table/new/:physicalTable',
          name: 'record-new-physical',
          component: () => import('@/views/RecordFormView.vue'),
        },
        {
          path: 'workspace/:table/:id',
          name: 'record-edit',
          component: () => import('@/views/RecordFormView.vue'),
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

function loginRoute(to) {
  const redirect = to?.fullPath && to.fullPath !== '/' ? to.fullPath : undefined
  return { name: 'login', query: redirect ? { redirect } : {} }
}

router.beforeEach(async (to) => {
  bootstrapSettings()

  if (to.meta.public) return true
  if (!isAuthenticated()) return loginRoute(to)

  // O workspace (menu + schema) carrega uma vez; se falhar, o AppShell mostra
  // o erro com «Tentar novamente» em vez de bloquear a navegação.
  if (!workspace.value) await loadWorkspace().catch(() => {})
  return true
})

// Sessão recusada pela API a meio do trabalho → volta ao login e regressa
// à mesma página depois de entrar.
window.addEventListener(UNAUTHORIZED_EVENT, () => {
  const current = router.currentRoute.value
  if (current.meta?.public) return
  workspace.value = null
  router.replace(loginRoute(current))
})

export default router
