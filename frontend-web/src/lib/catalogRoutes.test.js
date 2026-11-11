import { test } from 'node:test'
import assert from 'node:assert/strict'
import { hasModels } from './catalogRoutes.js'

test('hasModels: com a contagem da API, só as categorias com pelo menos um modelo mostrável', () => {
  assert.equal(hasModels({ nome: 'Almofada', modelos_visiveis: 2 }), true)
  assert.equal(hasModels({ nome: 'Guarda-Chuva', modelos_visiveis: 0 }), false)
  assert.equal(hasModels({ nome: 'Regional', modelos_visiveis: '0' }), false)
})

test('hasModels: sem a contagem (API antiga, lista da base de dados) não se sabe, e mostra-se', () => {
  assert.equal(hasModels({ nome: 'Almofada' }), true)
  assert.equal(hasModels({ nome: 'Almofada', modelos_visiveis: null }), true)
  assert.equal(hasModels(null), true)
})
