import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import {
  categoryMeta,
  clip,
  describeModel,
  modelMeta,
  pickerNoun,
  pretty,
  realDescription,
  sortDimensions,
  storeLabel,
} from './describe.js'

// Modelos reais (respostas da API guardadas para o e2e): o teste usa os mesmos dados que a loja.
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
const OCULOS = model('oculo/modelo-detalhe/slug/oculos/adulto')
const COLCHAO = model(
  'protetor_colchao/modelo-detalhe/slug/protetores-colchao/protetor-colchao-malha-texturizada',
)

test('realDescription: o texto «Sem descrição» dos dados antigos conta como vazio', () => {
  for (const placeholder of [
    'Sem descrição',
    'sem descricao',
    '  SEM DESCRIÇÃO  ',
    'Sem descrição.',
    '',
  ]) {
    assert.equal(realDescription(placeholder), '', JSON.stringify(placeholder))
  }
  for (const empty of [undefined, null, '   ']) assert.equal(realDescription(empty), '')
  assert.equal(realDescription('  Almofada macia.  '), 'Almofada macia.')
  // Só o texto que começa assim é o marcador: uma frase que o contém é uma descrição.
  assert.equal(realDescription('Tecido sem descrição de cor'), 'Tecido sem descrição de cor')
})

test('pretty: só a primeira letra passa a maiúscula («Material de Cozinha» não leva «De»)', () => {
  assert.equal(pretty('material de Cozinha'), 'Material de Cozinha')
  assert.equal(pretty('  óculos '), 'Óculos')
  assert.equal(pretty(undefined), '')
})

test('sortDimensions: por área, como os botões da ficha; o que não é medida fica no fim', () => {
  assert.deepEqual(sortDimensions(['140x200', '140x250', '140x300', '140x140']), [
    '140x140',
    '140x200',
    '140x250',
    '140x300',
  ])
  assert.deepEqual(sortDimensions(['90x200', '100x200', '200x200']), [
    '90x200',
    '100x200',
    '200x200',
  ])
  assert.deepEqual(sortDimensions(['Único', '35x50', '30x30']), ['30x30', '35x50', 'Único'])
  const original = ['2x2', '1x1']
  sortDimensions(original)
  assert.deepEqual(original, ['2x2', '1x1'], 'não altera a lista de entrada')
  assert.deepEqual(sortDimensions(undefined), [])
})

test('pickerNoun: medida(s), altura(s) ou opção/opções', () => {
  assert.deepEqual(pickerNoun({ format: 'dimensions', field: 'dimensoes' }), ['medida', 'medidas'])
  assert.deepEqual(pickerNoun({ format: 'plain', field: 'altura' }), ['altura', 'alturas'])
  assert.deepEqual(pickerNoun({ format: 'plain', field: 'cor' }), ['opção', 'opções'])
  assert.deepEqual(pickerNoun(undefined), ['opção', 'opções'])
})

test('storeLabel: tira as notas do backoffice do rótulo da loja', () => {
  assert.equal(storeLabel('Composição (%) — igual para todas as cores'), 'Composição')
  assert.equal(storeLabel('Dimensões (comprimento×largura)'), 'Dimensões (comprimento×largura)')
  assert.equal(storeLabel('Material do forro'), 'Material do forro')
  assert.equal(storeLabel(undefined), '')
})

test('describeModel: almofada com tipo, composição, medidas ordenadas e cores', () => {
  assert.equal(
    describeModel(FOGLIA),
    'Tipo: Decorativa. Composição: 100% Poliester. Disponível em 3 medidas (35x50, 45x45 e 60x60 cm) e em 5 cores.',
  )
})

test('describeModel: assento com materiais e alturas, sem cores (uma só cor não é informação)', () => {
  assert.equal(
    describeModel(LISO),
    'Material do forro: Poliéster. Material do enchimento: Poliuretano. Disponível em 2 alturas (32mm e 45mm).',
  )
})

test('describeModel: artigo único só com composição; óculos só com o tipo', () => {
  assert.equal(describeModel(AVENTAL), 'Composição: 100% Poliéster.')
  assert.equal(describeModel(OCULOS), 'Tipo: Óculos de sol.')
})

test('describeModel: muitas medidas dão o intervalo, não a lista inteira', () => {
  assert.equal(
    describeModel(COLCHAO),
    'Composição: 100% Poliéster. Disponível em 9 medidas (de 90x200 a 200x200 cm).',
  )
})

test('describeModel: duas fibras juntam-se com «e»; uma medida só; sem dados dá texto vazio', () => {
  const two = {
    _storefront: { specs: [{ field: 'composicao', label: 'Composição', widget: 'composition' }] },
    composicao: { Algodão: 60, Poliéster: 40 },
  }
  assert.equal(describeModel(two), 'Composição: 60% Algodão e 40% Poliéster.')

  const one = {
    _storefront: {
      product_table: 'product_variants',
      picker: { source: 'products', field: 'dimensoes', format: 'dimensions', suffix: ' cm' },
      specs: [],
    },
    product_variants: [{ ean: '5606044500001', dimensoes: '90x200' }],
  }
  assert.equal(describeModel(one), 'Disponível em 1 medida (90x200 cm).')

  for (const nothing of [undefined, null, {}, { nome: 'X', modelo_cores: [{ nome: 'Sortido' }] }]) {
    assert.equal(describeModel(nothing), '', JSON.stringify(nothing))
  }
})

test('describeModel: ignora variantes sem EAN, cores escondidas e especificações sem valor', () => {
  const m = {
    _storefront: {
      product_table: 'product_variants',
      picker: { source: 'products', field: 'dimensoes', format: 'dimensions', suffix: ' cm' },
      specs: [{ field: 'composicao', label: 'Composição', widget: 'composition' }],
    },
    composicao: {},
    product_variants: [
      { ean: '5606044500001', dimensoes: '45x45' },
      { ean: '', dimensoes: '99x99' },
    ],
    modelo_cores: [
      { nome: 'A', visibilidade: true },
      { nome: 'B', visibilidade: false },
      { nome: 'C' },
    ],
  }
  assert.equal(describeModel(m), 'Disponível em 1 medida (45x45 cm) e em 2 cores.')
})

test('clip: corta em palavra inteira e põe reticências só quando corta', () => {
  assert.equal(clip('curto'), 'curto')
  const long = `${'palavra '.repeat(30)}fim`
  const cut = clip(long, 40)
  assert.ok(cut.length <= 40, cut)
  assert.ok(cut.endsWith('…'), cut)
  assert.ok(!cut.slice(0, -1).endsWith(' '), cut)
  assert.equal(clip('a   b\n c'), 'a b c')
})

test('modelMeta: título «Modelo — Categoria» e descrição real, gerada ou genérica, nunca «Sem descrição»', () => {
  const real = modelMeta({ ...FOGLIA, descricao: 'Almofada em veludo.' }, 'Almofada')
  assert.deepEqual(real, {
    title: 'Foglia — Almofada',
    description: 'Almofada em veludo. Peça orçamento à Diomika.',
  })

  const generated = modelMeta(FOGLIA, 'Almofada') // descricao: «Sem descrição»
  assert.equal(generated.title, 'Foglia — Almofada')
  assert.equal(
    generated.description,
    'Tipo: Decorativa. Composição: 100% Poliester. Disponível em 3 medidas (35x50, 45x45 e 60x60 cm) e em 5 cores. Peça orçamento à Diomika.',
  )
  assert.ok(!/sem descri/i.test(generated.description))

  // Sem dados nenhuns: uma frase genérica, com o nome e a categoria.
  assert.deepEqual(modelMeta({ nome: 'Misterioso', descricao: 'Sem descrição' }, 'Guarda-Chuva'), {
    title: 'Misterioso — Guarda-Chuva',
    description: 'Misterioso — guarda-chuva. Peça orçamento à Diomika.',
  })
  assert.equal(modelMeta({ nome: 'Misterioso' }, '').title, 'Misterioso')
})

test('modelMeta: a descrição cabe nos 160 caracteres do resultado de pesquisa', () => {
  for (const m of [FOGLIA, LISO, AVENTAL, OCULOS, COLCHAO]) {
    const { description } = modelMeta(m, 'Categoria')
    assert.ok(description.length <= 160, `${m.nome}: ${description.length}`)
  }
  const long = modelMeta({ nome: 'X', descricao: 'palavra '.repeat(60) }, 'Y').description
  assert.ok(long.length <= 160 && long.endsWith('…'), long)
})

test('categoryMeta: o texto do pré-render, com o número de modelos quando se sabe', () => {
  assert.equal(
    categoryMeta('Almofada', 2),
    'Almofada: 2 modelos em várias cores e medidas. Peça orçamento à Diomika — pedido mínimo 500 € + IVA (615 € com IVA a 23 %).',
  )
  assert.match(categoryMeta('Assento', 1), /^Assento: 1 modelo em /)
  assert.match(categoryMeta('Assento'), /^Assento: modelos em várias cores e medidas\. /)
  assert.ok(!categoryMeta('Almofada', 2).includes(' '), 'espaços normais na meta description')
})
