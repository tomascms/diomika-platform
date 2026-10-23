import { onActivated, onBeforeUnmount, onDeactivated } from 'vue'

/**
 * Vistas dentro de KeepAlive só carregavam uma vez: mensagens e pedidos novos não apareciam
 * até reiniciar a app. Isto recarrega `refresh` ao voltar à vista e, com `intervalMs`, de
 * tempos a tempos enquanto está aberta e a janela visível.
 */
export function useAutoRefresh(refresh, intervalMs = 0) {
  let timer = null
  let firstActivation = true

  const stop = () => {
    clearInterval(timer)
    timer = null
  }

  onActivated(() => {
    if (!firstActivation) refresh()
    firstActivation = false
    if (intervalMs > 0) {
      stop()
      timer = setInterval(() => {
        if (document.visibilityState === 'visible') refresh()
      }, intervalMs)
    }
  })
  onDeactivated(stop)
  onBeforeUnmount(stop)
}
