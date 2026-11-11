/**
 * Chave de idempotência de um formulário (pedido de orçamento, contacto): a mesma até o envio ter sucesso, para um
 * reenvio (rede lenta, duplo clique, recarregar) não criar dois pedidos. Guarda-se no `sessionStorage`; com o
 * armazenamento bloqueado fica em memória (lib/storage.js).
 */
import { sessionStore } from './storage.js'

/** @param {string} storageKey o nome sob o qual a chave se guarda */
export function formKey(storageKey) {
  return {
    /** A chave desta sessão: cria-se à primeira vez e repete-se até `clear()`. */
    get() {
      let key = sessionStore.get(storageKey)
      if (!key) {
        key = crypto.randomUUID()
        sessionStore.set(storageKey, key)
      }
      return key
    },
    /** Depois de um envio com sucesso: o próximo pedido leva uma chave nova. */
    clear() {
      sessionStore.remove(storageKey)
    },
  }
}
