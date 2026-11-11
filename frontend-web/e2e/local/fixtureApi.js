// A API de produção, de mentira, em localhost: responde com as fixtures (e2e/local/fixtures), por caminho, como o
// `mockApi` faz no browser. Serve o pré-render a sério nos testes (scripts/prerender-seo.test.mjs e
// e2e/local/prerender.spec.js), que pede o catálogo a `VITE_API_BASE_URL`. Nunca sai de 127.0.0.1.
import { readFileSync } from 'node:fs'
import { createServer } from 'node:http'

const FIXTURES = new URL('./fixtures/', import.meta.url)
const readFixture = (name) => JSON.parse(readFileSync(new URL(`${name}.json`, FIXTURES), 'utf8'))

/**
 * @param {Record<string, () => [number, unknown]>} routes caminho → [estado, corpo], para trocar uma resposta
 *   (`{ '/categorias': () => [200, []] }`); o que não está lá sai das fixtures, ou dá 404
 * @param {(origin: string) => Promise<T>} run corre com a origem da API (`http://127.0.0.1:<porta>`)
 * @returns {Promise<T>}
 * @template T
 */
export async function withFixtureApi(routes, run) {
  const server = createServer((request, response) => {
    const { pathname } = new URL(request.url, 'http://localhost')
    let status = 200
    let body
    try {
      if (routes[pathname]) [status, body] = routes[pathname]()
      else body = readFixture(pathname.replace(/^\//, ''))
    } catch {
      status = 404
      body = { detail: 'Não encontrado' }
    }
    response.writeHead(status, { 'Content-Type': 'application/json' })
    response.end(JSON.stringify(body))
  })
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
  try {
    return await run(`http://127.0.0.1:${server.address().port}`)
  } finally {
    await new Promise((resolve) => server.close(resolve))
  }
}
