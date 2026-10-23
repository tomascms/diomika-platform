import { computed } from 'vue'
import { workspace } from './useWorkspace'

export function useAggregatedTipos() {
  const categoryDefinitions = computed(() => workspace.value?.catalog?.category_definitions || {})

  function getAggregatedTiposForCategory(category) {
    if (!category?.tipo_catalogo) return null
    for (const def of Object.values(categoryDefinitions.value || {})) {
      if (def.tipo_catalogo === category.tipo_catalogo && def.aggregated_tipos?.length) {
        return def.aggregated_tipos
      }
    }
    return null
  }

  return {
    getAggregatedTiposForCategory,
  }
}
