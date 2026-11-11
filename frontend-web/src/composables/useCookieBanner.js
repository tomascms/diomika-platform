import { nextTick, ref } from 'vue'

/**
 * Estado partilhado do banner de cookies (LEGAL-07): o `CookieBanner` mostra-o e mostra-o à primeira visita;
 * o rodapé e a política de cookies reabrem-no com `open()`, para o visitante mudar de escolha a qualquer momento.
 */
const visible = ref(false)
const reopened = ref(false) // aberto pelo visitante (rodapé), não pela primeira visita
let opener = null // o que o abriu: o foco volta para lá ao fechar

export function useCookieBanner() {
  /** @param {Element | null} [trigger] o botão que abriu o banner (por omissão, o elemento com foco) */
  const open = (trigger) => {
    opener = trigger ?? document.activeElement
    reopened.value = true
    visible.value = true
  }

  const close = () => {
    visible.value = false
    reopened.value = false
    const back = opener
    opener = null
    nextTick(() => back?.isConnected && back.focus())
  }

  return { visible, reopened, open, close }
}
