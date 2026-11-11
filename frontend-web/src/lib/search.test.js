import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { matchCategories, searchWords } from './search.js'

// As categorias reais da API (as das fixtures do e2e), sem as vazias: é o que a loja tem em memória.
const categories = JSON.parse(
  readFileSync(new URL('../../e2e/local/fixtures/categorias.json', import.meta.url), 'utf8'),
).filter((category) => category.modelos_visiveis > 0)

const found = (term) => matchCategories(term, categories).map((category) => category.nome)

test('searchWords: sem acentos, maiúsculas nem «s» final; as medidas escrevem-se de uma maneira só', () => {
  assert.deepEqual(searchWords('Óculos de Sol'), ['oculo', 'de', 'sol'])
  assert.deepEqual(searchWords('Guarda-Chuvas'), ['guarda', 'chuva'])
  assert.deepEqual(searchWords('45 x 45'), ['45x45'])
  assert.deepEqual(searchWords('45×45'), ['45x45'])
  assert.deepEqual(searchWords('32 mm'), ['32mm'])
  assert.deepEqual(searchWords('5606044199011'), ['5606044199011'])
  assert.deepEqual(searchWords('  '), [])
})

test('«almofada», «Almofada», «almofadas» e «ALMOFADA» encontram a categoria', () => {
  for (const term of ['almofada', 'Almofada', 'almofadas', 'ALMOFADA', ' almofada ']) {
    assert.deepEqual(found(term), ['Almofada'], term)
  }
})

test('«almofda», uma gralha (falta uma letra), e duas letras trocadas encontram a categoria', () => {
  for (const term of ['almofda', 'amlofada', 'almofadda', 'Almofdas']) {
    assert.deepEqual(found(term), ['Almofada'], term)
  }
})

test('com acentos ou sem eles, e com palavras de ligação', () => {
  assert.deepEqual(found('óculos'), ['Óculos'])
  assert.deepEqual(found('oculos'), ['Óculos'])
  assert.deepEqual(found('protetor colchao'), ['Protetor de Colchão'])
  assert.deepEqual(found('protetores de colchão'), ['Protetor de Colchão'])
  assert.deepEqual(found('toalhas de mesa'), ['Toalhas de Mesa'])
  assert.deepEqual(found('cozinha'), ['Material de Cozinha'])
})

test('palavras curtas não perdoam gralhas, e o que não é uma categoria não encontra nenhuma', () => {
  assert.deepEqual(found('assent'), ['Assento']) // parte do nome
  assert.deepEqual(found('asento'), ['Assento']) // uma gralha: falta um «s»
  assert.deepEqual(found('asent'), []) // duas letras a menos já é outra palavra
  assert.deepEqual(found('azul'), [])
  assert.deepEqual(found('45x45'), [])
  assert.deepEqual(found('5606044199011'), [])
  assert.deepEqual(found(''), [])
  // Só palavras vazias: usam-se mesmo assim, em vez de não haver pesquisa.
  assert.deepEqual(found('de'), ['Material de Cozinha', 'Protetor de Colchão', 'Toalhas de Mesa'])
})

test('todas as palavras têm de aparecer no nome', () => {
  assert.deepEqual(found('almofada azul'), [])
  assert.deepEqual(found('material cozinha'), ['Material de Cozinha'])
})

test('sem lista de categorias não há sugestões', () => {
  assert.deepEqual(matchCategories('almofada', []), [])
  assert.deepEqual(matchCategories('almofada', undefined), [])
})
