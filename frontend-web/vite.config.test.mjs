// `npm run dev` não usa a API de produção (auditoria FE-20).
//
// O servidor de desenvolvimento encaminha `/api` (GET e POST) para a API local por omissão. Antes era a de produção,
// e quem testava a loja localmente lia de produção e tentava escrever lá. O último teste arranca mesmo o servidor
// (`vite`, o que `npm run dev` corre) contra uma «API» falsa numa porta local e vê para onde vão os pedidos.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { createServer } from 'node:http'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import config, { devApiTarget } from './vite.config.js'

const HERE = path.dirname(fileURLToPath(import.meta.url))

test('devApiTarget: a API local por omissão, na porta da API local; outra só se se pedir', () => {
  assert.equal(devApiTarget({}), 'http://127.0.0.1:8001')
  assert.equal(devApiTarget({ DIOMIKA_API_PORT: '9001' }), 'http://127.0.0.1:9001')
  assert.equal(devApiTarget({ DIOMIKA_API_ORIGIN: 'https://api.exemplo.test/' }), 'https://api.exemplo.test')
  assert.equal(devApiTarget({ DIOMIKA_API_ORIGIN: '  ' }), 'http://127.0.0.1:8001')
})

test('o servidor de desenvolvimento encaminha /api para a API local, sem ler o .env de produção', async () => {
  const saved = process.env.DIOMIKA_API_ORIGIN
  delete process.env.DIOMIKA_API_ORIGIN
  try {
    const resolved = await config({ mode: 'development', command: 'serve' })
    assert.equal(resolved.server.proxy['/api'].target, 'http://127.0.0.1:8001')
    assert.ok(!JSON.stringify(resolved.server.proxy).includes('diomika.com'))
  } finally {
    if (saved !== undefined) process.env.DIOMIKA_API_ORIGIN = saved
  }
})

test('`npm run dev` é o vite deste projecto (o teste seguinte arranca-o como ele)', () => {
  const { scripts } = JSON.parse(readFileSync(path.join(HERE, 'package.json'), 'utf8'))
  assert.equal(scripts.dev, 'vite')
})

/** Uma «API» local que regista o que lhe chega. */
async function fakeApi() {
  /** @type {string[]} */
  const requests = []
  const server = createServer((req, res) => {
    requests.push(`${req.method} ${req.url}`)
    res.writeHead(200, { 'content-type': 'application/json' })
    res.end('{"da":"api local"}')
  })
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
  return { requests, port: server.address().port, close: () => server.close() }
}

/** Uma porta livre. */
async function freePort() {
  const probe = createServer()
  await new Promise((resolve) => probe.listen(0, '127.0.0.1', resolve))
  const { port } = probe.address()
  await new Promise((resolve) => probe.close(resolve))
  return port
}

test('com o servidor a correr, GET e POST em /api vão para a API local e nunca para fora', async () => {
  const api = await fakeApi()
  const port = await freePort()
  const env = { ...process.env, DIOMIKA_API_PORT: String(api.port) }
  delete env.DIOMIKA_API_ORIGIN
  const vite = spawn(process.execPath, [path.join(HERE, 'node_modules/vite/bin/vite.js'), '--port', String(port), '--strictPort'], {
    cwd: HERE,
    env,
    stdio: 'ignore',
  })
  try {
    const base = `http://127.0.0.1:${port}`
    let up = false
    for (let i = 0; i < 100 && !up; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 200))
      up = await fetch(base, { signal: AbortSignal.timeout(2000) }).then(() => true, () => false)
    }
    assert.ok(up, 'o servidor de desenvolvimento não arrancou')

    const get = await fetch(`${base}/api/categorias`)
    assert.equal(get.status, 200)
    assert.deepEqual(await get.json(), { da: 'api local' })
    const post = await fetch(`${base}/api/orcamentos`, { method: 'POST', body: '{}', headers: { 'content-type': 'application/json' } })
    assert.equal(post.status, 200)

    // O proxy tira o prefixo /api, e os dois pedidos chegaram à API local.
    assert.deepEqual(api.requests, ['GET /categorias', 'POST /orcamentos'])
  } finally {
    vite.kill()
    api.close()
  }
})
