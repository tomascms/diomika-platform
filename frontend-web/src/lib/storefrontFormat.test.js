import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import {
  collectEans,
  formatStorefrontValue,
  isSingleProductMode,
  showableModel,
  specRows,
  variantList,
} from './storefrontFormat.js'

const model = (path) =>
  JSON.parse(
    readFileSync(
      new URL(`../../e2e/local/fixtures/catalogo/${path}.json`, import.meta.url),
      'utf8',
    ),
  )
const FOGLIA = model('almofada/modelo-detalhe/slug/almofada/foglia')
const AVENTAL = model('avental/modelo-detalhe/slug/material-cozinha/avental-liso')
const LISO = model('assento/modelo-detalhe/slug/assento/liso')
const MESA = model('toalha_mesa/modelo-detalhe/slug/toalhas-mesa/protetor-de-mesa')

test('formatStorefrontValue: composição, listas, enumerados, sim/não, e o que não tem valor não se mostra', () => {
  assert.equal(
    formatStorefrontValue({ widget: 'composition' }, { Algodão: 60, Poliéster: 40 }),
    '60% Algodão, 40% Poliéster',
  )
  assert.equal(
    formatStorefrontValue({ widget: 'enum', enum_labels: { sol: 'Óculos de sol' } }, 'sol'),
    'Óculos de sol',
  )
  assert.equal(formatStorefrontValue({ widget: 'boolean' }, true), 'Sim')
  assert.equal(formatStorefrontValue({ widget: 'string_list' }, ['a', 'b']), 'a, b')
  assert.equal(formatStorefrontValue({ widget: 'integer' }, 180), '180')
  for (const empty of [null, undefined, ''])
    assert.equal(formatStorefrontValue({ widget: 'string' }, empty), null)
})

test('formatStorefrontValue: as medidas saem por ordem, como os botões da ficha (FE-16)', () => {
  const spec = { widget: 'dimension_list' }
  assert.equal(
    formatStorefrontValue(spec, ['140x200', '140x250', '140x300', '140x140']),
    '140x140, 140x200, 140x250, 140x300',
  )
  assert.equal(formatStorefrontValue(spec, ['90x200', '100x200']), '90x200, 100x200')
})

test('specRows: só as especificações com valor, com a composição em entradas e as medidas por ordem', () => {
  const rows = specRows(MESA, MESA._storefront.specs)

  assert.deepEqual(
    rows.map((row) => [row.field, row.display]),
    [
      ['composicao', '100% PVC'],
      ['dimensoes', '140x140, 140x200, 140x250, 140x300'],
    ],
  )
  assert.equal(rows[0].isComposition, true)
  assert.deepEqual(rows[0].compositionEntries, [['PVC', 100]])
  assert.equal(rows[1].isComposition, false)
})

test('specRows: um campo novo na lista de especificações aparece sem código por campo, e vazio não aparece', () => {
  const specs = [
    ...FOGLIA._storefront.specs,
    { field: 'gramagem', label: 'Gramagem (g/m²)', widget: 'integer', enum_labels: {} },
    { field: 'origem', label: 'País de origem', widget: 'string', enum_labels: {} },
    { field: 'prazo', label: 'Prazo de entrega', widget: 'string', enum_labels: {} },
  ]
  const rows = specRows({ ...FOGLIA, gramagem: 180, origem: '', prazo: null }, specs)

  assert.deepEqual(
    rows.map((row) => row.field),
    ['composicao', 'dimensoes', 'gramagem'],
  )
  assert.equal(rows[2].display, '180')
  assert.deepEqual(specRows(null, undefined), [])
  assert.deepEqual(specRows({}, [{ field: 'x', widget: 'string' }]), [])
})

test('showableModel: visível, com EAN e com uma cor visível', () => {
  assert.equal(showableModel(FOGLIA), true)
  // Artigo único: a linha de produto vem como objecto.
  assert.equal(showableModel(AVENTAL), true)
  assert.equal(showableModel({ ...FOGLIA, visibilidade: false }), false)
  assert.equal(
    showableModel({
      ...FOGLIA,
      product_variants: FOGLIA.product_variants.map((v) => ({ ...v, ean: '' })),
    }),
    false,
  )
  assert.equal(
    showableModel({
      ...FOGLIA,
      modelo_cores: FOGLIA.modelo_cores.map((c) => ({ ...c, visibilidade: false })),
    }),
    false,
  )
  assert.equal(showableModel({ ...FOGLIA, product_variants: [] }), false)
  assert.equal(showableModel(null), false)
})

test('isSingleProductMode: artigo único e selector sobre o modelo', () => {
  assert.equal(isSingleProductMode({ mode: 'unico' }), true)
  assert.equal(isSingleProductMode({ mode: 'variantes', picker: { source: 'model' } }), true)
  assert.equal(isSingleProductMode(FOGLIA._storefront), false)
  assert.equal(isSingleProductMode(undefined), false)
})

test('variantList: medida e EAN de cada variante, pela ordem dos botões da ficha', () => {
  assert.deepEqual(
    variantList(MESA).map((v) => v.measure),
    ['140x140 cm', '140x200 cm', '140x250 cm', '140x300 cm'],
  )
  const [first] = variantList(FOGLIA)
  assert.deepEqual(first, { measure: '35x50 cm', ean: '5606044506574' })
  assert.equal(variantList(FOGLIA).length, 3)
})

test('variantList: assento por altura, artigo único sem medida, sem EAN não conta', () => {
  assert.deepEqual(
    variantList(LISO).map((v) => v.measure),
    ['32mm', '45mm'],
  )
  assert.deepEqual(variantList(AVENTAL), [{ measure: '', ean: AVENTAL.product_variants.ean }])
  assert.deepEqual(variantList({ ...FOGLIA, product_variants: [{ ean: '' }] }), [])
  assert.deepEqual(variantList(null), [])
})

test('collectEans: todos os EAN de um modelo, em qualquer nível, numa lista ou num objecto só', () => {
  assert.deepEqual(collectEans(FOGLIA), ['5606044506574', '5606044506598', '5606044506734'])
  assert.deepEqual(collectEans(AVENTAL), [AVENTAL.product_variants.ean])
  assert.deepEqual(collectEans({ a: { b: [{ ean: 123 }, { ean: null }, { x: { ean: '9' } }] } }), [
    '123',
    '9',
  ])
  for (const nothing of [null, undefined, 'texto', 3, {}, []])
    assert.deepEqual(collectEans(nothing), [])
})
