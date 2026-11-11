import { test } from 'node:test'
import assert from 'node:assert/strict'
import { formKey } from './idempotency.js'

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

test('a chave repete-se até o envio ter sucesso, e a seguinte é outra', () => {
  const key = formKey('teste-idempotencia-a')
  const first = key.get()

  assert.match(first, UUID)
  assert.equal(key.get(), first, 'um reenvio leva a mesma chave')
  key.clear()
  const second = key.get()
  assert.match(second, UUID)
  assert.notEqual(second, first)
})

test('cada formulário tem a sua chave, e a mesma entrada devolve a mesma chave', () => {
  const quote = formKey('teste-idempotencia-orcamento')
  const contact = formKey('teste-idempotencia-contacto')

  assert.notEqual(quote.get(), contact.get())
  assert.equal(formKey('teste-idempotencia-orcamento').get(), quote.get())
  quote.clear()
  assert.notEqual(formKey('teste-idempotencia-orcamento').get(), contact.get())
})
