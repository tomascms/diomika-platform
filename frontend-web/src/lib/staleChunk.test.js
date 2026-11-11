import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  consumeReloadMark,
  installStaleChunkRecovery,
  isStaleChunkError,
  markReload,
  RELOAD_GAP_MS,
} from './staleChunk.js'

/** O router só com o que a recuperação usa; `fail` simula um erro de navegação. */
function fakeRouter() {
  const hooks = { before: [], error: [] }
  return {
    beforeEach: (hook) => hooks.before.push(hook),
    onError: (hook) => hooks.error.push(hook),
    navigate: (fullPath) => hooks.before.forEach((hook) => hook({ fullPath })),
    fail: (error, to) => hooks.error.forEach((hook) => hook(error, to)),
  }
}

const NOW = 1_000_000

/** Uma janela com o endereço, o `history` e os eventos que a recuperação usa. */
function fakeWindow(href = 'https://www.diomika.com/') {
  const win = new EventTarget()
  win.location = { href }
  win.history = {
    state: { back: '/' },
    replaced: [],
    replaceState(state, _title, url) {
      this.replaced.push(url)
    },
  }
  return win
}

function setup({ reloadedAt = null, href } = {}) {
  const router = fakeRouter()
  const win = fakeWindow(href)
  const visited = []
  let clock = NOW
  const recover = installStaleChunkRecovery(router, {
    reloadedAt,
    win,
    now: () => clock,
    go: (url) => visited.push(url),
  })
  return { router, win, visited, recover, tick: (ms) => (clock += ms) }
}

const CHROME = new TypeError(
  'Failed to fetch dynamically imported module: https://www.diomika.com/assets/AboutView-1a2b.js',
)
const marked = (path, at = NOW) => `${path}${path.includes('?') ? '&' : '?'}_recarregada=${at}`

test('reconhece o erro de um ficheiro que já não existe, em Chrome, Firefox e Safari', () => {
  assert.equal(isStaleChunkError(CHROME), true)
  assert.equal(
    isStaleChunkError(new TypeError('error loading dynamically imported module: x.js')),
    true,
  )
  assert.equal(isStaleChunkError(new TypeError('Importing a module script failed.')), true)
  assert.equal(isStaleChunkError(new Error('Cannot read properties of undefined')), false)
  assert.equal(isStaleChunkError(null), false)
})

test('markReload: a marca entra na query e a âncora fica onde estava', () => {
  assert.equal(markReload('/sobre', NOW), '/sobre?_recarregada=1000000')
  assert.equal(
    markReload('/pesquisa?q=almofada#topo', NOW),
    '/pesquisa?q=almofada&_recarregada=1000000#topo',
  )
  assert.equal(markReload('/sobre?_recarregada=1', NOW), '/sobre?_recarregada=1000000')
  assert.equal(
    markReload('https://www.diomika.com/contacto', NOW, 'https://www.diomika.com/'),
    '/contacto?_recarregada=1000000',
  )
})

test('consumeReloadMark: lê a hora, apaga a marca do endereço e deixa o resto', () => {
  const win = fakeWindow('https://www.diomika.com/pesquisa?q=almofada&_recarregada=999000#topo')

  assert.equal(consumeReloadMark(win), 999000)
  assert.deepEqual(win.history.replaced, ['/pesquisa?q=almofada#topo'])
})

test('consumeReloadMark: sem marca não toca no endereço', () => {
  const win = fakeWindow('https://www.diomika.com/sobre')

  assert.equal(consumeReloadMark(win), null)
  assert.deepEqual(win.history.replaced, [])
})

test('um ficheiro em falta ao navegar recarrega na página que a pessoa queria abrir', () => {
  const { router, visited } = setup()

  router.fail(CHROME, { fullPath: '/contacto?assunto=orcamento' })

  assert.deepEqual(visited, [marked('/contacto?assunto=orcamento')])
})

test('um erro que não é de ficheiro em falta não recarrega nada', () => {
  const { router, visited } = setup()

  router.fail(new Error('boom'), { fullPath: '/sobre' })

  assert.deepEqual(visited, [])
})

test('a falha a pré-carregar (evento do Vite) recarrega no destino da última navegação', () => {
  const { router, win, visited } = setup()

  router.navigate('/pesquisa?q=almofada')
  win.dispatchEvent(new Event('vite:preloadError'))

  assert.deepEqual(visited, [marked('/pesquisa?q=almofada')])
})

test('o evento do Vite sem navegação nenhuma recarrega a página atual', () => {
  const { win, visited } = setup({ href: 'https://www.diomika.com/categoria/almofada?cor=2' })

  win.dispatchEvent(new Event('vite:preloadError'))

  assert.deepEqual(visited, [marked('/categoria/almofada?cor=2')])
})

test('o erro do router e o evento do Vite da mesma falha recarregam uma só vez', () => {
  const { router, win, visited } = setup()

  router.navigate('/sobre')
  win.dispatchEvent(new Event('vite:preloadError'))
  router.fail(CHROME, { fullPath: '/sobre' })

  assert.deepEqual(visited, [marked('/sobre')])
})

test('se a página acabou de abrir depois de uma recuperação, não recarrega em ciclo; passado o intervalo, volta a tentar', () => {
  // A página nova leu a marca (consumeReloadMark): a anterior recarregou há 2 s.
  const { router, visited, tick } = setup({ reloadedAt: NOW - 2_000 })

  router.fail(CHROME, { fullPath: '/sobre' })
  assert.deepEqual(visited, [])

  tick(RELOAD_GAP_MS)
  router.fail(CHROME, { fullPath: '/sobre' })
  assert.deepEqual(visited, [marked('/sobre', NOW + RELOAD_GAP_MS)])
})

test('uma marca antiga (de há mais de 10 s) não impede recarregar', () => {
  const { router, visited } = setup({ reloadedAt: NOW - RELOAD_GAP_MS - 1 })

  router.fail(CHROME, { fullPath: '/sobre' })

  assert.deepEqual(visited, [marked('/sobre')])
})
