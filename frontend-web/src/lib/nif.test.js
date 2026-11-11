import { test } from 'node:test'
import assert from 'node:assert/strict'
import { isValidNif, NIF_ERROR, nifError, normalizeNif } from './nif.js'

// Os mesmos valores que backend-api/tests/test_quote_b2b.py. 508651557 é o NIPC da Diomika; os dois
// últimos, e 999999990, têm resto 0 ou 1 na soma ponderada (o dígito de controlo é 0 nos dois casos).
const VALID = ['508651557', '123456789', '999999990', '501442600', '100000010', '100000070']
const INVALID = [
  '508651558',
  '123456788',
  '123456780',
  '000000000',
  '12345678',
  '1234567890',
  'abcdefghi',
  '',
]

test('NIF português válido', () => {
  for (const nif of VALID) assert.equal(isValidNif(nif), true, nif)
})

test('NIF português inválido: dígito de controlo errado, tamanho errado, zeros, letras, vazio', () => {
  for (const nif of INVALID) assert.equal(isValidNif(nif), false, JSON.stringify(nif))
})

test('espaços, pontos, hífenes e o prefixo PT não contam', () => {
  for (const typed of [
    ' 508 651 557 ',
    '508.651.557',
    '508-651-557',
    'PT508651557',
    'pt 508 651 557',
  ]) {
    assert.equal(normalizeNif(typed), '508651557', typed)
    assert.equal(isValidNif(typed), true, typed)
  }
})

test('o que não é texto não é NIF válido (e não rebenta)', () => {
  for (const nif of [undefined, null, 508651557, {}, []]) assert.doesNotThrow(() => isValidNif(nif))
  assert.equal(isValidNif(undefined), false)
  assert.equal(isValidNif(null), false)
})

test('nifError: vazio e NIF português válido passam', () => {
  for (const nif of ['', '   ', undefined, null, '508651557', 'PT 508 651 557']) {
    assert.equal(nifError(nif), '', JSON.stringify(nif))
  }
})

test('nifError: um número português com o dígito de controlo errado é recusado em português', () => {
  for (const nif of ['508651558', 'PT123456788', '123 456 780']) {
    assert.equal(nifError(nif), NIF_ERROR, nif)
  }
  assert.match(NIF_ERROR, /^NIF inválido: o dígito de controlo não confere/)
})

test('nifError: um número estrangeiro (sem 9 dígitos) passa sem verificação', () => {
  for (const nif of ['ES B12345678', 'DE123456789', 'FR 12 345678901', '4567', '1234567890123']) {
    assert.equal(nifError(nif), '', nif)
  }
})
