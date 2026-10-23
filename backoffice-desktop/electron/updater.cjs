/**
 * Actualizações automáticas do Backoffice.
 *
 * Windows (instalador) e Linux (AppImage): o electron-updater descarrega a
 * versão nova em segundo plano e pergunta se quer reiniciar; se não, instala
 * ao fechar. O feed é privado (https://api.diomika.com/system/desktop-updates)
 * e só responde com o header do gate desktop.
 *
 * macOS sem assinatura da Apple não se pode auto-actualizar: aí só se avisa
 * que há uma versão nova.
 */
const { app, dialog, net } = require('electron')

const FEED_URL = 'https://api.diomika.com/system/desktop-updates'
const FIRST_CHECK_MS = 15 * 1000
const CHECK_EVERY_MS = 4 * 60 * 60 * 1000

function isNewer(remote, local) {
  const a = String(remote || '').split('.').map((n) => parseInt(n, 10) || 0)
  const b = String(local || '').split('.').map((n) => parseInt(n, 10) || 0)
  for (let i = 0; i < Math.max(a.length, b.length); i += 1) {
    if ((a[i] || 0) !== (b[i] || 0)) return (a[i] || 0) > (b[i] || 0)
  }
  return false
}

function fetchText(url, headers) {
  return new Promise((resolve, reject) => {
    const req = net.request({ method: 'GET', url })
    for (const [k, v] of Object.entries(headers)) req.setHeader(k, v)
    req.on('response', (res) => {
      const chunks = []
      res.on('data', (c) => chunks.push(Buffer.from(c)))
      res.on('end', () =>
        res.statusCode === 200 ? resolve(Buffer.concat(chunks).toString('utf8')) : reject(new Error(`HTTP ${res.statusCode}`)),
      )
    })
    req.on('error', reject)
    req.end()
  })
}

function setupMacNotice(headers, getWindow) {
  let notified = ''
  const check = async () => {
    try {
      const yml = await fetchText(`${FEED_URL}/latest-mac.yml`, headers)
      const version = (yml.match(/^version:\s*(\S+)/m) || [])[1]
      if (!version || version === notified || !isNewer(version, app.getVersion())) return
      notified = version
      await dialog.showMessageBox(getWindow() || undefined, {
        type: 'info',
        buttons: ['OK'],
        title: 'Nova versão disponível',
        message: `Há uma versão nova do Backoffice Diomika (${version}).`,
        detail: 'No Mac a actualização é manual: peça à Diomika o ficheiro .dmg mais recente.',
      })
    } catch {
      /* sem ligação ou sem versão publicada — tenta mais tarde */
    }
  }
  setTimeout(check, FIRST_CHECK_MS)
  setInterval(check, CHECK_EVERY_MS)
}

function setupAutoUpdates({ gate, getWindow }) {
  if (!app.isPackaged) return

  const headers = { 'User-Agent': `DiomikaBackoffice/${app.getVersion()}` }
  if (gate) headers['x-diomika-desktop'] = gate

  if (process.platform === 'darwin') {
    setupMacNotice(headers, getWindow)
    return
  }
  // Executável portátil não tem instalador onde aplicar a actualização.
  if (process.env.PORTABLE_EXECUTABLE_DIR) return
  if (process.platform === 'linux' && !process.env.APPIMAGE) return

  let autoUpdater
  try {
    ;({ autoUpdater } = require('electron-updater'))
  } catch (err) {
    console.warn('[updates] electron-updater indisponível:', err && err.message)
    return
  }

  autoUpdater.setFeedURL({ provider: 'generic', url: FEED_URL })
  autoUpdater.requestHeaders = headers
  autoUpdater.autoDownload = true
  autoUpdater.autoInstallOnAppQuit = true
  autoUpdater.allowDowngrade = false
  autoUpdater.logger = null

  autoUpdater.on('error', (err) => {
    console.warn('[updates]', (err && err.message) || err)
  })

  let prompted = ''
  autoUpdater.on('update-downloaded', async (info) => {
    if (!info || prompted === info.version) return
    prompted = info.version
    const { response } = await dialog.showMessageBox(getWindow() || undefined, {
      type: 'info',
      buttons: ['Reiniciar agora', 'Mais tarde'],
      defaultId: 0,
      cancelId: 1,
      title: 'Actualização pronta',
      message: `A versão ${info.version} do Backoffice Diomika está pronta a instalar.`,
      detail: 'Se escolher «Mais tarde», é instalada automaticamente quando fechar a aplicação.',
    })
    if (response === 0) setImmediate(() => autoUpdater.quitAndInstall(true, true))
  })

  const check = () => {
    autoUpdater.checkForUpdates().catch((err) => console.warn('[updates]', (err && err.message) || err))
  }
  setTimeout(check, FIRST_CHECK_MS)
  setInterval(check, CHECK_EVERY_MS)
}

module.exports = { setupAutoUpdates, isNewer }
