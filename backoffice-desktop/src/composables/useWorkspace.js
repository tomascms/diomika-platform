import { ref, computed } from 'vue'
import { api } from '@/lib/api'

export const workspace = ref(null)
export const loading = ref(false)
export const error = ref(null)

let loadPromise = null

export const sidebarItems = computed(() => {
  if (!workspace.value?.sidebar) return []
  return Object.entries(workspace.value.sidebar).map(([key, cfg]) => ({ key, ...cfg }))
})

export async function loadWorkspace(force = false) {
  if (!force && workspace.value) return workspace.value

  if (force) {
    workspace.value = null
    loadPromise = null
  }

  if (loadPromise) return loadPromise

  loadPromise = (async () => {
    loading.value = true
    error.value = null
    try {
      workspace.value = await api.workspace()
      return workspace.value
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
      loadPromise = null
    }
  })()

  return loadPromise
}

export function tableConfig(table) {
  return workspace.value?.tables?.[table] || null
}

export function useWorkspace() {
  return {
    workspace,
    sidebarItems,
    loading,
    error,
    load: loadWorkspace,
    loadWorkspace,
    tableConfig,
  }
}
