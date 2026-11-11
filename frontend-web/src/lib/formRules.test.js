import { test } from 'node:test'
import assert from 'node:assert/strict'
import { minLengthError, nameError } from './formRules.js'

test('nome: vazio fica para o «obrigatório»; 1 letra e só espaços são recusados; 2 letras passam', () => {
  assert.equal(nameError(''), '')
  assert.equal(nameError(undefined), '')
  for (const typed of ['A', '   ', ' A ', '\t\t']) {
    assert.equal(nameError(typed), 'O nome: mínimo de 2 caracteres.', JSON.stringify(typed))
  }
  for (const typed of ['Ana', 'Zé', ' Zé ', 'A B']) assert.equal(nameError(typed), '', typed)
})

test('mínimo de N caracteres, sem contar os espaços das pontas', () => {
  const message = minLengthError('A mensagem', 10)
  assert.equal(message(''), '')
  assert.equal(message('curta'), 'A mensagem: mínimo de 10 caracteres.')
  assert.equal(message('   curta   '), 'A mensagem: mínimo de 10 caracteres.')
  assert.equal(message('Gostaria de saber mais.'), '')
})
