import { test } from 'node:test'
import assert from 'node:assert/strict'
import { errorKind, fieldErrors } from './errors.js'

test('um endereço que já não existe ou que nem é um id: «not-found» (tentar de novo não resolve)', () => {
  for (const status of [404, 410, 400, 422])
    assert.equal(errorKind({ status }), 'not-found', String(status))
})

test('rede, tempo esgotado, erro do servidor e o que não se conhece: «unavailable»', () => {
  for (const err of [
    { status: 500 },
    { status: 502 },
    { status: 503 },
    { status: 429 },
    { network: true },
    new Error('x'),
    null,
    undefined,
  ]) {
    assert.equal(errorKind(err), 'unavailable', JSON.stringify(err))
  }
})

test('fieldErrors: um 422 da API vira {campo: mensagem}', () => {
  const body = {
    detail: [
      { type: 'string_too_short', loc: ['body', 'nome'], msg: 'O nome: mínimo de 2 caracteres.' },
      {
        type: 'value_error',
        loc: ['body', 'email'],
        msg: 'Indique um email válido, por exemplo nome@empresa.pt.',
      },
    ],
  }
  assert.deepEqual(fieldErrors(body), {
    nome: 'O nome: mínimo de 2 caracteres.',
    email: 'Indique um email válido, por exemplo nome@empresa.pt.',
  })
})

test('fieldErrors: guarda só o primeiro erro de cada campo e usa o último texto de `loc`', () => {
  const body = {
    detail: [
      { loc: ['body', 'linhas', 0, 'quantidade'], msg: 'A quantidade: mínimo de 1.' },
      { loc: ['body', 'linhas', 1, 'quantidade'], msg: 'A quantidade: mínimo de 6.' },
      { loc: ['body', 7], msg: 'O pedido não está bem formado.' },
    ],
  }
  assert.deepEqual(fieldErrors(body), { quantidade: 'A quantidade: mínimo de 1.' })
})

test('fieldErrors: o que não é uma lista de erros dá {}', () => {
  for (const body of [
    null,
    undefined,
    {},
    { detail: 'Pedido invalido' },
    { detail: { msg: 'x' } },
    { detail: [null, {}] },
  ]) {
    assert.deepEqual(fieldErrors(body), {}, JSON.stringify(body))
  }
})
