import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  cartSummaryText,
  itemKey,
  lineMeta,
  normalizeCartItems,
  toQuoteLines,
} from './quoteLines.js'

const item = { ean: '5606044506574', numero_cor: '12', quantidade: '24' }
const linha = { ean: '5606044506574', numero_cor: 12, quantidade: 24 }

test('altura objecto (carrinho antigo, modos unico/leitura) não segue no pedido', () => {
  assert.deepEqual(toQuoteLines([{ ...item, altura: { id: 1, ean: 'x' } }]), [linha])
})

test('altura em texto mantém-se', () => {
  assert.deepEqual(toQuoteLines([{ ...item, altura: '32mm' }]), [{ ...linha, altura: '32mm' }])
})

test('altura vazia ou que não é texto não segue no pedido', () => {
  for (const altura of ['', undefined, null, 32, [], ['32mm']]) {
    assert.deepEqual(
      toQuoteLines([{ ...item, altura }]),
      [linha],
      `altura: ${JSON.stringify(altura)}`,
    )
  }
})

test('mapeia todas as linhas, pela ordem', () => {
  const out = toQuoteLines([
    { ean: '5600000000013', numero_cor: 1, quantidade: 6 },
    { ean: '5600000000037', numero_cor: 2, quantidade: 12, altura: '45mm' },
  ])
  assert.deepEqual(out, [
    { ean: '5600000000013', numero_cor: 1, quantidade: 6 },
    { ean: '5600000000037', numero_cor: 2, quantidade: 12, altura: '45mm' },
  ])
})

// Carrinho lido do browser: pode ter linhas guardadas antes da correcção FE-01 (altura = produto inteiro).
const produto = { id: 'p-1', ean: '5600000000051', visibilidade: true, barcode_url: '' }
const antiga = {
  ean: '5600000000051',
  numero_cor: 1,
  quantidade: 12,
  modeloNome: 'Luva',
  dimensoes: 'Referência',
  altura: produto,
}
const nova = {
  ean: '5600000000051',
  numero_cor: 1,
  quantidade: 6,
  modeloNome: 'Luva',
  dimensoes: 'Referência',
}
const juntas = {
  ean: '5600000000051',
  numero_cor: 1,
  quantidade: 18,
  modeloNome: 'Luva',
  dimensoes: 'Referência',
}

test('itemKey: EAN|cor|altura (o formato que removeItem e updateQty também usam)', () => {
  assert.equal(itemKey({ ean: '5600000000051', numero_cor: 1 }), '5600000000051|1|')
  assert.equal(
    itemKey({ ean: '5600000000037', numero_cor: '5', altura: '32mm' }),
    '5600000000037|5|32mm',
  )
})

test('linha antiga (altura objecto) + linha nova do mesmo produto e cor ficam numa só, com a soma das quantidades', () => {
  assert.deepEqual(normalizeCartItems([antiga, nova]), [juntas])
})

test('altura que não é texto (ou vazia) é removida; altura em texto mantém-se', () => {
  for (const altura of [produto, '', null, 32, [], ['32mm']]) {
    assert.deepEqual(
      normalizeCartItems([{ ...nova, altura }]),
      [nova],
      `altura: ${JSON.stringify(altura)}`,
    )
  }
  const comTexto = { ean: '5600000000037', numero_cor: 2, quantidade: 12, altura: '32mm' }
  assert.deepEqual(normalizeCartItems([comTexto]), [comTexto])
})

test('só junta linhas com a mesma chave (EAN, cor, altura); a junta fica na posição da primeira', () => {
  const b = { ean: '5600000000037', numero_cor: 1, quantidade: 12, altura: '32mm' }
  const c = { ean: '5600000000037', numero_cor: 1, quantidade: 12, altura: '45mm' }
  const d = { ean: '5600000000037', numero_cor: 2, quantidade: 12, altura: '32mm' }
  assert.deepEqual(normalizeCartItems([antiga, b, c, d, nova]), [juntas, b, c, d])
})

test('soma as quantidades como números e fica com os dados da linha mais recente', () => {
  const [linha] = normalizeCartItems([
    { ...antiga, quantidade: '12', imagem: 'antiga.webp' },
    { ...nova, imagem: 'nova.webp' },
  ])
  assert.equal(linha.quantidade, 18) // não '126'
  assert.equal(linha.imagem, 'nova.webp')
})

test('não altera o carrinho de entrada e é idempotente', () => {
  const entrada = [antiga, nova]
  const copia = structuredClone(entrada)
  const uma = normalizeCartItems(entrada)
  assert.deepEqual(entrada, copia)
  assert.deepEqual(normalizeCartItems(uma), uma)
})

test('lineMeta: medida com « cm», altura sem unidade, e «Referência»/«Sortido» não são medidas', () => {
  assert.equal(
    lineMeta({ dimensoes: '45x45', numero_cor: 12, corNome: 'Azul Ciano' }),
    '45x45 cm · Cor 12 (Azul Ciano)',
  )
  assert.equal(
    lineMeta({ dimensoes: '32mm', altura: '32mm', numero_cor: 1, corNome: 'Sortido' }),
    '32mm · Cor 1 (Sortido)',
  )
  assert.equal(
    lineMeta({ dimensoes: 'Referência', numero_cor: 1, corNome: 'Sortido' }),
    'Cor 1 (Sortido)',
  )
  assert.equal(lineMeta({ dimensoes: 'Sortido', numero_cor: 2 }), 'Cor 2')
  assert.equal(lineMeta({ numero_cor: 3 }), 'Cor 3')
})

test('cartSummaryText: artigos e unidades, no singular e no plural (RP-17)', () => {
  assert.equal(cartSummaryText({ lines: 1, units: 12 }), '1 artigo · 12 un.')
  assert.equal(cartSummaryText({ lines: 2, units: 72 }), '2 artigos · 72 un.')
  assert.equal(cartSummaryText({ lines: 0, units: 0 }), '0 artigos · 0 un.')
})
