import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { findByEan, MAX_QUOTE_LINES, parseQuickOrder, resolveQuickLine } from './quickOrder.js'

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

const EAN = '5606044506574' // Foglia 35x50
const hits = (...models) => models.map((m) => ({ model: m, category: m.categories }))
const found = (m, ean) => findByEan(ean, hits(m))

test('parseQuickOrder: «EAN; cor; quantidade» com ponto e vírgula, vírgula, tabulação (folha de cálculo) ou espaços', () => {
  for (const raw of [
    `${EAN}; 12; 240`,
    `${EAN},12,240`,
    `${EAN}\t12\t240`,
    `${EAN} 12 240`,
    `  ${EAN} ;12;240 ;`,
  ]) {
    const { rows, errors } = parseQuickOrder(raw)
    assert.deepEqual(errors, [], raw)
    assert.deepEqual(rows, [{ n: 1, raw: raw.trim(), ean: EAN, color: 12, quantity: 240 }], raw)
  }
})

test('parseQuickOrder: sem cor (artigos de uma só cor), linhas em branco e numeração das linhas', () => {
  const { rows, errors } = parseQuickOrder(`\n${EAN}; 240\n\r\n  \n5606044506598;13;12\n`)
  assert.deepEqual(errors, [])
  assert.deepEqual(
    rows.map(({ n, ean, color, quantity }) => ({ n, ean, color, quantity })),
    [
      { n: 2, ean: EAN, color: null, quantity: 240 },
      { n: 5, ean: '5606044506598', color: 13, quantity: 12 },
    ],
  )
  assert.deepEqual(parseQuickOrder(''), { rows: [], errors: [] })
  assert.deepEqual(parseQuickOrder(undefined), { rows: [], errors: [] })
})

test('parseQuickOrder: cada linha má dá o seu motivo, em português, e as boas seguem', () => {
  const text = [
    'abc; 1; 2', // 1: EAN
    `${EAN}; 0; 12`, // 2: cor
    `${EAN}; x; 12`, // 3: cor
    `${EAN}; 12; 0`, // 4: quantidade
    `${EAN}; 12; 12.5`, // 5: quantidade
    `${EAN}; 12; -3`, // 6: quantidade
    EAN, // 7: campos a menos
    `${EAN}; 1; 2; 3`, // 8: campos a mais
    `${EAN}; 12; 24`, // 9: boa
    `${EAN}; 12; 48`, // 10: repetida
    `${EAN}; 13; 48`, // 11: outra cor do mesmo EAN: boa
  ].join('\n')
  const { rows, errors } = parseQuickOrder(text)

  assert.deepEqual(
    rows.map((r) => r.n),
    [9, 11],
  )
  const FORMAT = 'Escreva «EAN; cor; quantidade» (a cor pode faltar nos artigos de uma só cor).'
  const COR = 'A cor é o número da cor (por exemplo, 12).'
  const QUANTIDADE = 'A quantidade é um número inteiro (por exemplo, 240).'
  assert.deepEqual(
    errors.map(({ n, message }) => [n, message]),
    [
      [1, 'O EAN tem 13 dígitos.'],
      [2, COR],
      [3, COR],
      [4, QUANTIDADE],
      [5, QUANTIDADE],
      [6, QUANTIDADE],
      [7, FORMAT],
      [8, FORMAT],
      [10, 'Repetido: este artigo já está na linha 9.'],
    ],
  )
})

test('findByEan: o modelo que tem exactamente este EAN (a pesquisa também devolve EAN parecidos)', () => {
  const other = {
    ...LISO,
    product_variants: LISO.product_variants.map((v) => ({ ...v, ean: `${v.ean.slice(0, 12)}0` })),
  }
  const result = findByEan(EAN, hits(other, FOGLIA))
  assert.equal(result.model.nome, 'Foglia')
  assert.equal(result.product.ean, EAN)
  assert.equal(result.category.carrinho_step, 12)
  assert.equal(findByEan('5606044599999', hits(FOGLIA)), null)
  assert.equal(findByEan(EAN, []), null)
  assert.equal(findByEan(EAN, undefined), null)
})

test('resolveQuickLine: a linha do pedido tem o que a ficha junta, e diz o que ficou', () => {
  const result = resolveQuickLine({ ean: EAN, color: 12, quantity: 240 }, found(FOGLIA, EAN))
  assert.equal(result.ok, true)
  assert.equal(result.label, 'Foglia · 35x50 cm · Cor 12 (Azul Ciano): 240 un.')
  assert.equal(result.notice, '')
  assert.deepEqual(result.item, {
    ean: EAN,
    numero_cor: 12,
    altura: undefined,
    quantidade: 240,
    modeloNome: 'Foglia',
    dimensoes: '35x50',
    corNome: 'Azul Ciano',
    carrinhoStep: 12,
    carrinhoMin: 12,
    imagem: '',
  })
  assert.equal(result.color.nome, 'Azul Ciano')
})

test('resolveQuickLine: um múltiplo inválido sobe ao seguinte, com o mesmo aviso da ficha', () => {
  const result = resolveQuickLine({ ean: EAN, color: 12, quantity: 100 }, found(FOGLIA, EAN))
  assert.equal(result.item.quantidade, 108)
  assert.equal(
    result.notice,
    'Quantidade ajustada de 100 para 108 un.: vendemos em múltiplos de 12.',
  )
  const toalha = TOALHA.product_variants[0].ean
  assert.equal(
    resolveQuickLine({ ean: toalha, color: 1, quantity: 7 }, found(TOALHA, toalha)).item.quantidade,
    12,
  )
})

test('resolveQuickLine: artigos de uma só cor dispensam a cor; a altura do assento e o artigo único', () => {
  const liso = LISO.product_variants.find((v) => v.altura === '32mm').ean
  const assento = resolveQuickLine({ ean: liso, color: null, quantity: 12 }, found(LISO, liso))
  assert.equal(assento.label, 'Liso · 32mm · Cor 1 (Sortido): 12 un.')
  assert.equal(assento.item.altura, '32mm')

  const avental = AVENTAL.product_variants.ean
  const unico = resolveQuickLine(
    { ean: avental, color: null, quantity: 24 },
    found(AVENTAL, avental),
  )
  assert.equal(unico.label, 'Avental Liso · Cor 1 (Sortido): 24 un.')
  assert.equal(unico.item.dimensoes, '')
})

test('resolveQuickLine: o motivo de cada recusa', () => {
  assert.deepEqual(resolveQuickLine({ ean: '5606044599999', color: 1, quantity: 12 }, null), {
    ok: false,
    message: 'O EAN 5606044599999 não existe no catálogo.',
  })
  assert.deepEqual(resolveQuickLine({ ean: EAN, color: null, quantity: 12 }, found(FOGLIA, EAN)), {
    ok: false,
    message: 'Foglia: indique a cor. As cores são 12, 13, 18, 21, 22.',
  })
  assert.deepEqual(resolveQuickLine({ ean: EAN, color: 99, quantity: 12 }, found(FOGLIA, EAN)), {
    ok: false,
    message: 'Foglia: a cor 99 não existe. As cores são 12, 13, 18, 21, 22.',
  })
  const hidden = {
    ...FOGLIA,
    modelo_cores: FOGLIA.modelo_cores.map((c) => ({ ...c, visibilidade: false })),
  }
  assert.deepEqual(resolveQuickLine({ ean: EAN, color: 12, quantity: 12 }, found(hidden, EAN)), {
    ok: false,
    message: 'Foglia: não tem cores disponíveis.',
  })
})

test('o pedido aceita, no máximo, 50 linhas (como a API)', () => {
  assert.equal(MAX_QUOTE_LINES, 50)
})
