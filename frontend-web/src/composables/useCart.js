const STORAGE_KEY = 'diomika_cart'

function itemKey(item) {
  return `${item.ean}|${item.numero_cor}|${item.altura || ''}`
}

function loadRaw() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveRaw(items) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  window.dispatchEvent(new CustomEvent('diomika-cart-updated'))
}

export function buildQtyOptions(step = 6, min = 6, max = 6000) {
  const { step: s, min: m } = resolveCartQtyRules({ carrinho_step: step, carrinho_min: min })
  const opts = []
  for (let q = m; q <= max; q += s) {
    opts.push(q)
  }
  return opts
}

/** Regras de quantidade alinhadas com backend (min fallback = step). */
export function resolveCartQtyRules(source = {}) {
  const step = Number(source.carrinho_step ?? source.carrinhoStep) || 6
  const minRaw = source.carrinho_min ?? source.carrinhoMin
  const min = minRaw != null && minRaw !== '' ? Number(minRaw) : step
  return { step, min: Math.max(min, step) }
}

export function isValidCartQty(qty, source = {}) {
  const { step, min } = resolveCartQtyRules(source)
  const q = Number(qty)
  return q >= min && q <= 6000 && q % step === 0
}

export function useCart() {
  const getItems = () => loadRaw()

  const count = () => loadRaw().reduce((n, i) => n + (i.quantidade || 0), 0)

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
    const items = loadRaw().map((i) =>
      itemKey(i) === key ? { ...i, quantidade } : i,
    )
    saveRaw(items)
    return items
  }

  const clear = () => {
    saveRaw([])
  }

  return { getItems, count, addItem, removeItem, updateQty, clear, buildQtyOptions }
}
