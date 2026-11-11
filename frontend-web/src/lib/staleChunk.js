/**
 * Separador aberto antes de um deploy (auditoria FE-12). Cada deploy troca os ficheiros de `/assets/` por outros com
 * outro nome e apaga os antigos: quem tinha a loja aberta clicava em «Contacto» ou «Pesquisar», o navegador pedia um
 * ficheiro que já não existe (404) e nada acontecia até recarregar à mão. Aqui a loja recarrega-se sozinha, na
 * página que a pessoa queria abrir.
 *
 * Só recarrega uma vez de cada 10 s: se o ficheiro faltar mesmo depois de recarregar (um problema do servidor, não
 * uma versão nova), recarregar outra vez não resolve e criava um ciclo. A marca de que acabou de recarregar vai no
 * endereço (`?_recarregada=<hora>`), que a página nova lê e apaga ao arrancar: não se guarda nada no navegador (a
 * política de cookies lista tudo o que a loja guarda) e funciona também com o armazenamento bloqueado.
 */

// Chrome e Edge, Firefox e Safari dizem a mesma coisa de maneiras diferentes.
const STALE_CHUNK =
  /dynamically imported module|Importing a module script failed|error loading dynamically imported/i

/** O erro de um `import()` de um ficheiro que deixou de existir (não um erro do código da página). */
export function isStaleChunkError(error) {
  return STALE_CHUNK.test(String(error?.message ?? error ?? ''))
}

const MARK = '_recarregada'
export const RELOAD_GAP_MS = 10_000

/** O endereço com a marca de «recarregada agora»: relativo (caminho, query e âncora), para ficar no mesmo sítio. */
export function markReload(url, now, base = 'http://localhost') {
  const target = new URL(url, base)
  target.searchParams.set(MARK, String(now))
  return `${target.pathname}${target.search}${target.hash}`
}

/**
 * Se a página abriu depois de uma recuperação, lê a hora na marca e apaga-a do endereço (a loja não a mostra nem a
 * guarda). Chamar antes de criar o router: ele lê o endereço ao ser criado.
 * @returns {number | null} a hora a que a página anterior recarregou, ou null
 */
export function consumeReloadMark(win = window) {
  const url = new URL(win.location.href)
  const raw = url.searchParams.get(MARK)
  if (raw === null) return null
  url.searchParams.delete(MARK)
  win.history.replaceState(win.history.state, '', `${url.pathname}${url.search}${url.hash}`)
  return Number(raw) || null
}

const goTo = (url) => window.location.assign(url)

/**
 * Liga o router e o evento `vite:preloadError` (falha a pré-carregar o CSS ou o JS de um ficheiro) à recuperação.
 * @param {{ beforeEach: Function, onError: Function }} router
 * @param {{ reloadedAt?: number | null, win?: Window, now?: () => number, go?: (url: string) => void }} [options]
 *   `reloadedAt`: o que devolveu `consumeReloadMark`
 * @returns {(url?: string | null) => boolean} a recuperação, `true` se mandou recarregar
 */
export function installStaleChunkRecovery(
  router,
  { reloadedAt = null, win = window, now = Date.now, go = goTo } = {},
) {
  // O destino da última navegação: o evento do Vite não o traz, e recarregar na página de partida deixava
  // a pessoa onde estava.
  let target = null
  let lastReload = reloadedAt

  const recover = (url = target) => {
    if (lastReload && now() - lastReload < RELOAD_GAP_MS) return false
    lastReload = now()
    go(markReload(url ?? win.location.href, lastReload, win.location.href))
    return true
  }

  router.beforeEach((to) => {
    target = to.fullPath
  })
  router.onError((error, to) => {
    if (isStaleChunkError(error)) recover(to?.fullPath)
  })
  win.addEventListener('vite:preloadError', () => recover())
  return recover
}
