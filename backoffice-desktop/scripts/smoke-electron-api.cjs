/** Smoke: electron.net → api.diomika.com (mesmo stack do backoffice instalado). */
const { app, net } = require('electron')
const path = require('path')

const API = (process.env.DIOMIKA_API_ORIGIN || 'https://api.diomika.com').replace(/\/+$/, '')

function loadGate() {
  try {
    return String(require(path.join(__dirname, '../electron/desktop-gate.cjs')) || '').trim()
  } catch {
    return (process.env.DIOMIKA_DESKTOP_GATE || '').trim()
  }
}

function get(url) {
  return new Promise((resolve, reject) => {
    const req = net.request({ method: 'GET', url })
    req.setHeader('User-Agent', 'DiomikaBackoffice/1.0')
    req.setHeader('accept-encoding', 'identity')
    const gate = loadGate()
    if (gate) req.setHeader('x-diomika-desktop', gate)
    req.on('response', (res) => {
      const chunks = []
      res.on('data', (c) => chunks.push(c))
      res.on('end', () =>
        resolve({ status: res.statusCode, body: Buffer.concat(chunks).toString('utf8').slice(0, 200) }),
      )
    })
    req.on('error', reject)
    req.end()
  })
}

app.whenReady().then(async () => {
  try {
    const health = await get(`${API}/health`)
    const auth = await get(`${API}/admin/auth/status`)
    console.log('health', health.status, health.body)
    console.log('auth', auth.status, auth.body)
    const ok = health.status === 200 && auth.status === 200
    app.exit(ok ? 0 : 1)
  } catch (err) {
    console.error('FAIL', err.message || err)
    app.exit(1)
  }
})
