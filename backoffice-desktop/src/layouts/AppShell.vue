<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter, RouterView } from 'vue-router'
import { useWorkspace } from '@/composables/useWorkspace'
import { clearSession, readSessionUser } from '@/lib/settings'
import { api, clearApiCaches } from '@/lib/api'
import Sidebar from '@/components/Sidebar.vue'

const HEALTH_RETRY_MS = 15000

const route = useRoute()
const router = useRouter()
const { sidebarItems, loadWorkspace, workspace, error, loading } = useWorkspace()
const currentTable = computed(() => route.params.table || '')
const sidebarOpen = ref(false)
const sessionUser = ref(readSessionUser())
const apiOnline = ref(null)
const retrying = ref(false)

const pageTitle = computed(() =>
  workspace.value?.sidebar?.[currentTable.value]?.label
    || workspace.value?.tables?.[currentTable.value]?.label
    || 'Painel',
)

let healthTimer = null

async function checkHealth() {
  try {
    await api.health()
    apiOnline.value = true
  } catch {
    apiOnline.value = false
  }
}

// Sem ligação → volta a tentar sozinho; quando a API regressa, recarrega o
// menu se ele tinha falhado. O utilizador não tem de reabrir a app.
watch(apiOnline, (online, wasOnline) => {
  clearInterval(healthTimer)
  if (online === false) {
    healthTimer = setInterval(checkHealth, HEALTH_RETRY_MS)
  } else if (online && wasOnline === false && !workspace.value) {
    loadWorkspace(true).catch(() => {})
  }
})

async function retryAll() {
  retrying.value = true
  try {
    await checkHealth()
    await loadWorkspace(true).catch(() => {})
  } finally {
    retrying.value = false
  }
}

async function logout() {
  try {
    await api.logout()
  } catch {
    clearApiCaches()
  }
  clearSession()
  sessionUser.value = null
  workspace.value = null
  await router.replace({ name: 'login' })
}

function onBrowserOnline() {
  void checkHealth()
}

onMounted(() => {
  void checkHealth()
  if (!workspace.value) loadWorkspace().catch(() => {})
  api.me()
    .then((me) => {
      sessionUser.value = { username: me.username, role: me.role }
    })
    .catch(() => {})
  window.addEventListener('online', onBrowserOnline)
})

onBeforeUnmount(() => {
  clearInterval(healthTimer)
  window.removeEventListener('online', onBrowserOnline)
})

watch(() => route.fullPath, () => {
  sidebarOpen.value = false
})

const bannerMessage = computed(() => {
  if (apiOnline.value === false) {
    return 'Sem ligação à API. As alterações não são guardadas até a ligação voltar — a app volta a tentar sozinha.'
  }
  if (error.value) return `Não foi possível carregar o menu: ${error.value}`
  return ''
})

const viewKey = computed(() => (route.name === 'workspace' ? 'workspace' : route.fullPath))
</script>

<template>
  <div class="shell" :class="{ 'sidebar-open': sidebarOpen }">
    <div v-if="sidebarOpen" class="overlay" @click="sidebarOpen = false" />

    <Sidebar
      :items="sidebarItems"
      :active="currentTable"
      :loading="loading"
      :online="apiOnline"
      :user="sessionUser"
      @navigate="sidebarOpen = false"
      @logout="logout"
    />

    <div class="main">
      <header class="topbar">
        <button
          type="button"
          class="menu-btn btn btn-ghost btn-icon"
          aria-label="Abrir menu"
          :aria-expanded="sidebarOpen"
          @click="sidebarOpen = !sidebarOpen"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
        </button>
        <h1 class="page-title">{{ pageTitle }}</h1>
        <span
          class="status-chip"
          :class="{ online: apiOnline, offline: apiOnline === false }"
          role="status"
        >
          <span class="dot" aria-hidden="true" />
          {{ apiOnline ? 'Ligado' : apiOnline === false ? 'Sem ligação' : 'A ligar…' }}
        </span>
      </header>

      <div v-if="bannerMessage" class="banner" role="alert">
        <p>{{ bannerMessage }}</p>
        <button type="button" class="btn btn-secondary btn-sm" :disabled="retrying" @click="retryAll">
          {{ retrying ? 'A tentar…' : 'Tentar agora' }}
        </button>
      </div>

      <main class="content">
        <RouterView v-slot="{ Component }">
          <KeepAlive :include="['WorkspaceRouter']" :max="4">
            <component :is="Component" :key="viewKey" />
          </KeepAlive>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--sidebar-w) minmax(0, 1fr);
  height: 100vh;
  background: var(--bg);
}

.main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  height: var(--header-height);
  padding: 0 28px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  flex: none;
}

.menu-btn {
  display: none;
}

.page-title {
  flex: 1;
  min-width: 0;
  font-size: 18px;
  font-weight: 650;
  font-stretch: 108%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 12.5px;
  font-weight: 560;
  white-space: nowrap;
}

.status-chip .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-chip.online .dot {
  background: var(--success);
}

.status-chip.offline {
  color: var(--danger);
  border-color: var(--danger);
  background: var(--danger-soft);
}

.status-chip.offline .dot {
  background: var(--danger);
}

.banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 16px 28px 0;
  padding: 10px 14px;
  border-radius: var(--radius);
  background: var(--warning-soft);
  color: var(--warning);
  font-size: 13.5px;
  font-weight: 500;
}

.content {
  flex: 1;
  min-height: 0;
  padding: 24px 28px 40px;
  overflow-y: auto;
  overflow-x: hidden;
}

.overlay {
  display: none;
}

@media (max-width: 900px) {
  .shell {
    grid-template-columns: minmax(0, 1fr);
  }

  .menu-btn {
    display: inline-flex;
  }

  .topbar {
    padding: 0 12px;
  }

  .banner {
    margin: 12px 12px 0;
  }

  .content {
    padding: 16px 12px 32px;
  }

  .overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(10, 14, 18, 0.45);
    z-index: 90;
  }

  .shell :deep(.sidebar) {
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 100;
    width: min(280px, 86vw);
    transform: translateX(-105%);
    transition: transform 180ms cubic-bezier(0.2, 0, 0, 1);
    box-shadow: var(--shadow-lg);
  }

  .shell.sidebar-open :deep(.sidebar) {
    transform: translateX(0);
  }
}
</style>
