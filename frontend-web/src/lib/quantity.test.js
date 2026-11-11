import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  adjustQuantity,
  boxNote,
  isValidCartQty,
  MAX_QTY,
  normalizeQuantity,
  resolveCartQtyRules,
} from './quantity.js'

test('normalizeQuantity: o múltiplo do passo por excesso (100 com passo 12 passa a 108)', () => {
  assert.equal(normalizeQuantity(100, 12, 12), 108)
  assert.equal(normalizeQuantity(13, 6, 6), 18)
  assert.equal(normalizeQuantity(7, 6, 6), 12)
  assert.equal(normalizeQuantity(12.5, 12, 12), 24)
})

test('normalizeQuantity: um múltiplo certo não muda; números em texto contam', () => {
  assert.equal(normalizeQuantity(120, 12, 12), 120)
  assert.equal(normalizeQuantity(6000, 12, 12), 6000)
  assert.equal(normalizeQuantity('240', 12, 12), 240)
  assert.equal(normalizeQuantity(' 36 ', 6, 6), 36)
})

test('normalizeQuantity: nunca abaixo do mínimo', () => {
  for (const value of [0, 1, 11, -5])
    assert.equal(normalizeQuantity(value, 12, 12), 12, String(value))
  // Mínimo que não é múltiplo do passo: a primeira quantidade válida é o múltiplo seguinte.
  assert.equal(normalizeQuantity(5, 10, 12), 12)
  assert.equal(normalizeQuantity(5, 18, 12), 24)
  // Mínimo abaixo do passo (a loja usa max(mínimo, passo)).
  assert.equal(normalizeQuantity(6, 6, 12), 12)
})

test('normalizeQuantity: nunca acima do máximo, que também é múltiplo do passo', () => {
  assert.equal(MAX_QTY, 6000)
  assert.equal(normalizeQuantity(6001, 12, 12), 6000)
  assert.equal(normalizeQuantity(99999, 6, 6), 6000)
  // 6000 não é múltiplo de 7: o último válido é 5999.
  assert.equal(normalizeQuantity(6000, 7, 7), 5999)
  assert.equal(normalizeQuantity(1000, 12, 12, 100), 96)
})

test('normalizeQuantity: o que não é número dá o mínimo (e não rebenta)', () => {
  for (const value of ['', '  ', 'abc', undefined, null, NaN, Infinity, {}, []]) {
    assert.equal(normalizeQuantity(value, 12, 12), 12, JSON.stringify(value))
  }
})

test('normalizeQuantity: o resultado é sempre válido pela regra do pedido (mínimo, múltiplo, até 6000)', () => {
  // A mesma regra de isValidCartQty (composables/useCart.js).
  const valid = (q, min, step) => q >= Math.max(min, step) && q <= 6000 && q % step === 0
  for (const [min, step] of [
    [12, 12],
    [6, 6],
    [6, 12],
    [10, 12],
    [18, 12],
    [1, 1],
    [7, 7],
    [5, 3],
  ]) {
    for (const value of [-1, 0, 1, 2, 5, 6, 7, 11, 12, 13, 100, 999, 5999, 6000, 6001, 123456]) {
      assert.ok(
        valid(normalizeQuantity(value, min, step), min, step),
        `${value} (mínimo ${min}, passo ${step})`,
      )
    }
  }
})

test('adjustQuantity: sem alteração não há aviso', () => {
  assert.deepEqual(adjustQuantity(240, 12, 12), { value: 240, notice: '' })
  assert.deepEqual(adjustQuantity('12', 12, 12), { value: 12, notice: '' })
})

test('adjustQuantity: um múltiplo inválido é corrigido e o aviso diz de quanto para quanto e porquê', () => {
  assert.deepEqual(adjustQuantity(100, 12, 12), {
    value: 108,
    notice: 'Quantidade ajustada de 100 para 108 un.: vendemos em múltiplos de 12.',
  })
  assert.deepEqual(adjustQuantity('13', 6, 6), {
    value: 18,
    notice: 'Quantidade ajustada de 13 para 18 un.: vendemos em múltiplos de 6.',
  })
})

test('adjustQuantity: abaixo do mínimo e acima do máximo dizem o limite', () => {
  assert.deepEqual(adjustQuantity(5, 12, 12), {
    value: 12,
    notice: 'Quantidade ajustada de 5 para 12 un.: o mínimo é 12 un.',
  })
  assert.deepEqual(adjustQuantity(7000, 12, 12), {
    value: 6000,
    notice: 'Quantidade ajustada de 7000 para 6000 un.: o máximo por pedido é 6000 un.',
  })
})

test('boxNote: só diz «caixas de N» quando o passo é a caixa', () => {
  assert.equal(boxNote(12, 12), 'Vendido em caixas de 12 un.')
  assert.equal(boxNote('6', 6), 'Vendido em caixas de 6 un.')
  for (const [box, step] of [
    [12, 6],
    [6, 12],
    [undefined, 12],
    [null, 12],
    ['', 12],
    [0, 0],
    ['abc', 12],
    [12.5, 12],
  ]) {
    assert.equal(boxNote(box, step), '', `${box} / ${step}`)
  }
})

test('resolveCartQtyRules: lê a categoria (carrinho_*) e a linha do pedido (carrinho*); o mínimo nunca é menor do que o passo', () => {
  assert.deepEqual(resolveCartQtyRules({ carrinho_step: 12, carrinho_min: 12 }), {
    step: 12,
    min: 12,
  })
  assert.deepEqual(resolveCartQtyRules({ carrinhoStep: 6, carrinhoMin: 6 }), { step: 6, min: 6 })
  assert.deepEqual(resolveCartQtyRules({ carrinho_step: 12, carrinho_min: 6 }), {
    step: 12,
    min: 12,
  })
  assert.deepEqual(resolveCartQtyRules({ carrinho_step: 12 }), { step: 12, min: 12 })
  assert.deepEqual(resolveCartQtyRules({}), { step: 6, min: 6 })
  assert.deepEqual(resolveCartQtyRules(undefined), { step: 6, min: 6 })
})

test('isValidCartQty: mínimo, múltiplo do passo e até 6000', () => {
  const category = { carrinho_step: 12, carrinho_min: 12 }
  for (const q of [12, 24, 240, 6000]) assert.equal(isValidCartQty(q, category), true, String(q))
  for (const q of [0, 6, 13, 6012, 7000, NaN])
    assert.equal(isValidCartQty(q, category), false, String(q))
})
