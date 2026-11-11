/**
 * Armazenamento do navegador que nunca lança (FE-11). Com os dados do site bloqueados, até aceder a
 * `localStorage` ou `sessionStorage` lança SecurityError: antes, a loja ficava em branco ou o botão
 * «Adicionar ao pedido» não fazia nada. Aqui o que não se consegue guardar fica em memória, enquanto a
 * página estiver aberta, e `set` diz se ficou guardado no navegador (`true`) ou só em memória (`false`).
 */
export function createStore(getArea) {
  const memory = new Map()
  // O acesso a `window.localStorage` também pode lançar: tudo dentro do `try`.
  const area = () => {
    try {
      return getArea() ?? null
    } catch {
      return null
    }
  }

  return {
    get(key) {
      if (memory.has(key)) return memory.get(key)
      try {
        return area()?.getItem(key) ?? null
      } catch {
        return null
      }
    },
    /** `true` se ficou guardado no navegador; `false` se só em memória (armazenamento bloqueado ou cheio). */
    set(key, value) {
      try {
        const store = area()
        if (!store) throw new Error('sem armazenamento')
        store.setItem(key, value)
        memory.delete(key)
        return true
      } catch {
        memory.set(key, String(value))
        return false
      }
    },
    remove(key) {
      memory.delete(key)
      try {
        area()?.removeItem(key)
      } catch {
        /* nada guardado, nada a apagar */
      }
    },
  }
}

export const localStore = createStore(() => window.localStorage)
export const sessionStore = createStore(() => window.sessionStorage)
