/**
 * Testa o proxy local /api → API (mesmo caminho do .exe instalado).
 * Falha se upRes.pipe(res) ou headers estiverem errados.
 */
const { app, net } = require('electron')
const http = require('http')
const path = require('path')

const API_ORIGIN = 'https://api.diomika.com'

function loadGate() {
  try {
    return String(require(path.join(__dirname, '../electron/desktop-gate.cjs')) || '').trim()
  } catch {
    return ''
  }
}

const GATE = loadGate()

function proxyToApi(req, res) {
  const incoming = new URL(req.url || '/', 'http://127.0.0.1')
  const targetPath = (incoming.pathname.replace(/^\/api/, '') || '/') + incoming.search
  const targetUrl = `${API_ORIGIN}${targetPath}`

  const upstream = net.request({ method: 'GET', url: targetUrl, redirect: 'follow' })
  upstream.setHeader('accept-encoding', 'identity')
  upstream.setHeader('user-agent', 'DiomikaBackoffice/1.0')
  if (GATE) upstream.setHeader('x-diomika-desktop', GATE)

  upstream.on('response', (upRes) => {
    const chunks = []
    upRes.on('data', (c) => chunks.push(Buffer.from(c)))
    upRes.on('end', () => {
      res.writeHead(upRes.statusCode || 502, { 'Content-Type': 'application/json' })
      res.end(Buffer.concat(chunks))
    })
    upRes.on('error', (e) => {
      res.writeHead(502)
      res.end(JSON.stringify({ detail: e.message }))
    })
  })
  upstream.on('error', (e) => {
    res.writeHead(502)
    res.end(JSON.stringify({ detail: e.message }))
  })
  upstream.end()
}

function fetchLocal(port, path) {
  return new Promise((resolve, reject) => {
    http
      .get(`http://127.0.0.1:${port}${path}`, (r) => {
        const chunks = []
        r.on('data', (c) => chunks.push(c))
        r.on('end', () => resolve({ status: r.statusCode, body: Buffer.concat(chunks).toString('utf8') }))
      })
      .on('error', reject)
  })
}

app.whenReady().then(async () => {
  const server = http.createServer((req, res) => proxyToApi(req, res))
  await new Promise((resolve, reject) => {
    server.listen(0, '127.0.0.1', resolve)
    server.on('error', reject)
  })
  const port = server.address().port
  try {
    const health = await fetchLocal(port, '/api/health')
    const auth = await fetchLocal(port, '/api/admin/auth/status')
    console.log('proxy health', health.status, health.body.slice(0, 80))
    console.log('proxy auth', auth.status, auth.body.slice(0, 80))
    server.close()
    app.exit(health.status === 200 && auth.status === 200 ? 0 : 1)
  } catch (err) {
    console.error('FAIL', err.message || err)
    server.close()
    app.exit(1)
  }
})
