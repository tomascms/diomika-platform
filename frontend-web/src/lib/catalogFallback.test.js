import { test } from 'node:test'
import assert from 'node:assert/strict'
import { withDatabaseFallback } from './catalogFallback.js'

// Como o ApiError de lib/api.js: `status` (0 sem resposta) e `network`.
const apiError = (fields) => Object.assign(new Error('api'), fields)
const CONFIGURED = { configured: true }

/** Conta as chamadas à base de dados. */
const database = (result) => {
  const calls = []
  return {
    calls,
    run: async () => (calls.push(1), typeof result === 'function' ? result() : result),
  }
}

test('a API respondeu: é o que se devolve, e a base de dados nem se toca', async () => {
  const db = database({ id: 'da-bd' })
  const result = await withDatabaseFallback(async () => ({ id: 'da-api' }), db.run, CONFIGURED)

  assert.deepEqual(result, { id: 'da-api' })
  assert.equal(db.calls.length, 0)
})

test('sem rede, com tempo esgotado ou com erro do servidor, a base de dados responde em vez da API', async () => {
  for (const failure of [
    { status: 0, network: true },
    { status: 0, network: true, timeout: true },
    { status: 500 },
    { status: 503 },
  ]) {
    const db = database({ id: 'da-bd' })
    const result = await withDatabaseFallback(
      () => Promise.reject(apiError(failure)),
      db.run,
      CONFIGURED,
    )

    assert.deepEqual(result, { id: 'da-bd' }, JSON.stringify(failure))
    assert.equal(db.calls.length, 1)
  }
})

test('404 e 422 são «não existe»: não há recurso e o erro da API é o que fica', async () => {
  for (const status of [400, 404, 410, 422]) {
    const db = database({ id: 'da-bd' })
    const error = apiError({ status })

    await assert.rejects(
      withDatabaseFallback(() => Promise.reject(error), db.run, CONFIGURED),
      (caught) => caught === error,
    )
    assert.equal(db.calls.length, 0, String(status))
  }
})

test('sem base de dados configurada o erro da API segue tal e qual', async () => {
  const db = database({ id: 'da-bd' })
  const error = apiError({ status: 0, network: true })

  await assert.rejects(
    withDatabaseFallback(() => Promise.reject(error), db.run, { configured: false }),
    (caught) => caught === error,
  )
  assert.equal(db.calls.length, 0)
})

test('se o recurso também falhar, o erro que se mostra é o da API (rede ou servidor), não o da base de dados', async () => {
  const error = apiError({ status: 502 })
  const db = database(() => {
    throw new Error('Categoria não encontrada.')
  })

  await assert.rejects(
    withDatabaseFallback(() => Promise.reject(error), db.run, CONFIGURED),
    (caught) => caught === error,
  )
  assert.equal(db.calls.length, 1)
})
