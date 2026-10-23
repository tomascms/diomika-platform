/**
 * Reproduz pedidos do renderer (sec-fetch-*) através do proxy — falha se ERR_INVALID_ARGUMENT.
 */
const { app, net } = require('electron')
const http = require('http')
const path = require('path')

const API_ORIGIN = 'https://api.diomika.com'

const FORWARD_HEADERS = new Set([
  'accept',
  'content-type',
  'authorization',
  'x-api-key',
  'idempotency-key',
])

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
  upstream.setHeader('accept', 'application/json')
  if (GATE) upstream.setHeader('x-diomika-desktop', GATE)

  for (const [key, value] of Object.entries(req.headers)) {
    const lower = key.toLowerCase()
    if (!FORWARD_HEADERS.has(lower)) continue
    upstream.setHeader(key, String(value))
  }

  upstream.on('response', (upRes) => {
    const chunks = []
    upRes.on('data', (c) => chunks.push(Buffer.from(c)))
    upRes.on('end', () => {
      res.writeHead(upRes.statusCode || 502, { 'Content-Type': 'application/json' })
      res.end(Buffer.concat(chunks))
    })
  })
  upstream.on('error', (e) => {
    res.writeHead(502, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ detail: e.message }))
  })
  upstream.end()
}

function fetchLocal(port, reqPath, headers) {
  return new Promise((resolve, reject) => {
    const req = http.request(
      { hostname: '127.0.0.1', port, path: reqPath, method: 'GET', headers },
      (r) => {
        const chunks = []
        r.on('data', (c) => chunks.push(c))
        r.on('end', () => resolve({ status: r.statusCode, body: Buffer.concat(chunks).toString('utf8') }))
      },
    )
    req.on('error', reject)
    req.end()
  })
}

app.whenReady().then(async () => {
  const server = http.createServer((req, res) => proxyToApi(req, res))
  await new Promise((resolve, reject) => {
    server.listen(0, '127.0.0.1', resolve)
    server.on('error', reject)
  })
  const port = server.address().port
  const browserHeaders = {
    accept: '*/*',
    'accept-language': 'pt-PT,pt;q=0.9',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
    'sec-ch-ua': '"Chromium";v="130"',
    referer: `http://127.0.0.1:${port}/`,
    'user-agent': 'Mozilla/5.0',
  }
  try {
    const health = await fetchLocal(port, '/api/health', browserHeaders)
    const auth = await fetchLocal(port, '/api/admin/auth/status', browserHeaders)
    console.log('browser-proxy health', health.status, health.body.slice(0, 60))
    console.log('browser-proxy auth', auth.status, auth.body.slice(0, 60))
    server.close()
    const ok = health.status === 200 && auth.status === 200 && !health.body.includes('ERR_INVALID')
    app.exit(ok ? 0 : 1)
  } catch (err) {
    console.error('FAIL', err.message || err)
    server.close()
    app.exit(1)
  }
})
