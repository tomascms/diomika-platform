/**
 * Verificações de origem da janela e do servidor local (SEG-15). Funções puras, testadas com `node --test`.
 */

/** A origem completa, não o prefixo: `http://127.0.0.1.outro-dominio.com/` não é a app. */
function isAppOrigin(url, appOrigin) {
  try {
    return Boolean(appOrigin) && new URL(url).origin === appOrigin
  } catch {
    return false
  }
}

/** O servidor local só atende quem fala com `127.0.0.1:<porta>` (ou `localhost:<porta>`): um nome vindo de um DNS-rebinding não passa. */
function hostAllowed(hostHeader, port) {
  const host = String(hostHeader || '').toLowerCase()
  return Boolean(port) && (host === `127.0.0.1:${port}` || host === `localhost:${port}`)
}

module.exports = { isAppOrigin, hostAllowed }
