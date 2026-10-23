import { ref } from 'vue'
import { apiGet } from '@/lib/api'
import { resolveImageUrls, PLACEHOLDER, needsPrivateSign } from '@/lib/images'
import { listCategories } from '@/lib/catalogSupabase'

/** Estado partilhado — App.vue e HomeView usam a mesma instância. */
const categories = ref([])
const loading = ref(false)
const error = ref('')
let loadPromise = null

const CACHE_KEY = 'diomika_cats_v6'
const CACHE_TTL_MS = 5 * 60 * 1000

function readCatCache() {
  try {
    ;['diomika_cats_v1', 'diomika_cats_v2', 'diomika_cats_v3', 'diomika_cats_v5'].forEach((k) =>
      sessionStorage.removeItem(k),
    )
  } catch {
    /* ignore */
  }
  try {
    const raw = sessionStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const bag = JSON.parse(raw)
    if (!bag?.at || !Array.isArray(bag.data) || Date.now() - bag.at > CACHE_TTL_MS) return null
    return bag.data
  } catch {
    return null
  }
}

function writeCatCache(data) {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify({ at: Date.now(), data }))
  } catch {
    /* ignore */
  }
}

async function hydrateCategoryImages(list) {
  const need = (list || []).filter((c) => c && c.imagem && needsPrivateSign(c.imagem))
  if (!need.length) return list
  const urls = await resolveImageUrls(
    need.map((c) => c.imagem),
    PLACEHOLDER,
  )
  need.forEach((c, i) => {
    const next = urls[i]
    // Só substitui se obtivemos signed URL real — nunca gravar placeholder no cache
    if (next && next !== PLACEHOLDER && !String(next).includes('placeholder')) {
      c.imagem = next
    }
  })
  categories.value = [...categories.value]
  writeCatCache(categories.value)
  return list
}

export function useCategories() {
  const load = async (force = false) => {
    if (categories.value.length && !force) {
      return categories.value
    }
    if (loadPromise) {
      return loadPromise
    }

    if (!force) {
      const cached = readCatCache()
      if (cached?.length) {
        categories.value = cached.map((c) => ({ ...c }))
        // Mostra já a cópia guardada e vai buscar a lista actual por trás: o
        // que se publicar no backoffice substitui-a no ecrã assim que chega.
        void hydrateCategoryImages(categories.value)
        void load(true).catch(() => {})
        return categories.value
      }
    }

    loading.value = true
    error.value = ''
    loadPromise = (async () => {
      try {
        let raw
        try {
          const data = await apiGet('/categorias')
          raw = (Array.isArray(data) ? data : []).filter((c) => c.visibilidade !== false)
        } catch {
          const data = await listCategories()
          raw = (Array.isArray(data) ? data : []).filter((c) => c.visibilidade !== false)
        }
        categories.value = raw.map((c) => ({ ...c }))
        writeCatCache(categories.value)
        loading.value = false
        void hydrateCategoryImages(categories.value)
        return categories.value
      } catch (e) {
        // Numa revalidação em segundo plano mantém-se o que já está no ecrã.
        if (!categories.value.length) {
          error.value = e.message || 'Erro ao carregar categorias.'
        }
        throw e
      } finally {
        loading.value = false
        loadPromise = null
      }
    })()

    return loadPromise
  }

  return { categories, loading, error, load }
}
