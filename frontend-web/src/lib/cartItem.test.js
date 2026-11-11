import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { cartItemFor } from './cartItem.js'

const model = (path) =>
  JSON.parse(
    readFileSync(
      new URL(`../../e2e/local/fixtures/catalogo/${path}.json`, import.meta.url),
      'utf8',
    ),
  )
const FOGLIA = model('almofada/modelo-detalhe/slug/almofada/foglia')
const LISO = model('assento/modelo-detalhe/slug/assento/liso')
const AVENTAL = model('avental/modelo-detalhe/slug/material-cozinha/avental-liso')
const TOALHA = model('toalha_mesa/modelo-detalhe/slug/toalhas-mesa/toalha-natal')

const line = (m, product, color, quantity) =>
  cartItemFor({ model: m, category: m.categories, product, color, quantity, image: '/img.webp' })

test('variantes: a medida da variante, sem altura', () => {
  const [product] = FOGLIA.product_variants
  assert.deepEqual(line(FOGLIA, product, FOGLIA.modelo_cores[0], 240), {
    ean: '5606044506574',
    numero_cor: 12,
    altura: undefined,
    quantidade: 240,
    modeloNome: 'Foglia',
    dimensoes: '35x50',
    corNome: 'Azul Ciano',
    carrinhoStep: 12,
    carrinhoMin: 12,
    imagem: '/img.webp',
  })
})

test('assento: a altura (texto) segue como altura e como medida', () => {
  const product = LISO.product_variants.find((v) => v.altura === '45mm')
  const item = line(LISO, product, LISO.modelo_cores[0], 12)
  assert.equal(item.altura, '45mm')
  assert.equal(item.dimensoes, '45mm')
})

test('artigo único: sem medida («Referência» não é uma) e sem altura', () => {
  // A API manda a linha de produto de um artigo único como objecto, não como lista.
  const item = line(AVENTAL, AVENTAL.product_variants, AVENTAL.modelo_cores[0], 12)
  assert.equal(item.dimensoes, '')
  assert.equal(item.altura, undefined)
})

test('as regras de quantidade são as da categoria (toalhas de mesa: 6 em 6)', () => {
  const item = line(TOALHA, TOALHA.product_variants[0], TOALHA.modelo_cores[0], 6)
  assert.deepEqual([item.carrinhoStep, item.carrinhoMin], [6, 6])
})
