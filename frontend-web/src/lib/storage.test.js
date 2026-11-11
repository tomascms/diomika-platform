import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createStore } from './storage.js'

/** Um `Storage` mínimo, com o que o código usa. */
const fakeArea = () => {
  const data = new Map()
  return {
    data,
    getItem: (key) => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => void data.set(key, String(value)),
    removeItem: (key) => void data.delete(key),
  }
}

test('com armazenamento: lê, escreve e apaga no navegador', () => {
  const area = fakeArea()
  const store = createStore(() => area)

  assert.equal(store.get('a'), null)
  assert.equal(store.set('a', '1'), true)
  assert.equal(area.data.get('a'), '1')
  assert.equal(store.get('a'), '1')
  store.remove('a')
  assert.equal(area.data.has('a'), false)
  assert.equal(store.get('a'), null)
})

test('armazenamento bloqueado (o acesso lança SecurityError): nada lança e fica em memória', () => {
  const store = createStore(() => {
    throw new DOMException('The operation is insecure.', 'SecurityError')
  })

  assert.equal(store.get('cart'), null)
  assert.equal(store.set('cart', '[1]'), false) // não ficou no navegador
  assert.equal(store.get('cart'), '[1]') // mas a página vê-o
  assert.equal(store.set('cart', '[1,2]'), false)
  assert.equal(store.get('cart'), '[1,2]')
  assert.doesNotThrow(() => store.remove('cart'))
  assert.equal(store.get('cart'), null)
})

test('armazenamento cheio (setItem lança): o valor fica em memória e a leitura vê-o', () => {
  const area = fakeArea()
  area.setItem = () => {
    throw new DOMException('quota', 'QuotaExceededError')
  }
  const store = createStore(() => area)

  assert.equal(store.set('k', 'v'), false)
  assert.equal(store.get('k'), 'v')
})

test('depois de falhar, uma escrita que resulta passa a valer e a memória larga o valor antigo', () => {
  const area = fakeArea()
  let full = true
  const original = area.setItem
  area.setItem = (key, value) => {
    if (full) throw new DOMException('quota', 'QuotaExceededError')
    original(key, value)
  }
  const store = createStore(() => area)

  store.set('k', 'em memória')
  full = false
  assert.equal(store.set('k', 'no navegador'), true)
  assert.equal(area.data.get('k'), 'no navegador')
  assert.equal(store.get('k'), 'no navegador')
})

test('só os valores em texto: o que se guarda sai em texto, como no Storage', () => {
  const store = createStore(() => {
    throw new Error('bloqueado')
  })
  store.set('n', 12)
  assert.equal(store.get('n'), '12')
})

test('getItem a lançar: devolve null em vez de rebentar', () => {
  const area = fakeArea()
  area.getItem = () => {
    throw new Error('ilegível')
  }
  assert.equal(createStore(() => area).get('x'), null)
})
