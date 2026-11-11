import { ref } from 'vue'
import { isValidCartQty, resolveCartQtyRules } from '@/lib/quantity'
import { captureEvent } from '@/lib/posthog'
import { itemKey, normalizeCartItems } from '@/lib/quoteLines'
import { localStore } from '@/lib/storage'

const STORAGE_KEY = 'diomika_cart'

// Verdadeiro quando o navegador não deixa guardar o pedido (dados do site bloqueados, ou cheios): o pedido fica em
// memória até se fechar ou recarregar a página, e a loja avisa (StorageNotice.vue). FE-11.
const storageBlocked = ref(false)

function loadRaw() {
  try {
    const raw = localStore.get(STORAGE_KEY)
    // Carrinhos antigos (FE-01) trazem `altura` como objecto: normaliza-se sempre que se lê.
    return raw ? normalizeCartItems(JSON.parse(raw)) : []
  } catch {
    return []
  }
}

function saveRaw(items) {
  storageBlocked.value = !localStore.set(STORAGE_KEY, JSON.stringify(items))
  window.dispatchEvent(new CustomEvent('diomika-cart-updated'))
}

export { isValidCartQty, resolveCartQtyRules }

export function useCart() {
  const getItems = () => loadRaw()

  // Artigos (linhas) e unidades: o cabeçalho mostra os artigos, o nome acessível diz as duas coisas (FE-07, RP-17).
  const summary = () => {
    const items = loadRaw()
    return {
      lines: items.length,
      units: items.reduce((n, i) => n + (Number(i.quantidade) || 0), 0),
    }
  }

  const addItem = (item) => {
    const items = loadRaw()
    const key = itemKey(item)
    const idx = items.findIndex((i) => itemKey(i) === key)
    if (idx >= 0) {
      items[idx] = { ...items[idx], ...item }
    } else {
      items.push(item)
    }
    saveRaw(items)
    // Só com consentimento (captureEvent não faz nada sem ele): que artigos se juntam ao pedido (RP-10).
    captureEvent('add_to_quote', {
      ean: item.ean,
      model: item.modeloNome,
      quantity: item.quantidade,
    })
    return items
  }

  const removeItem = (ean, numeroCor, altura = '') => {
    const key = `${ean}|${numeroCor}|${altura || ''}`
    const items = loadRaw().filter((i) => itemKey(i) !== key)
    saveRaw(items)
    return items
  }

  const updateQty = (ean, numeroCor, quantidade, altura = '') => {
    const key = `${ean}|${numeroCor}|${altura || ''}`
    const items = loadRaw().map((i) => (itemKey(i) === key ? { ...i, quantidade } : i))
    saveRaw(items)
    return items
  }

  const clear = () => {
    saveRaw([])
  }

  return { getItems, summary, addItem, removeItem, updateQty, clear, storageBlocked }
}
