import test from 'node:test'
import assert from 'node:assert/strict'
import { bundleBody, colorItems, variantItems } from './bundle.js'

let n = 0
const newId = () => `novo-${++n}`

test('cores: as novas levam id; as gravadas mantêm o seu; linhas sem número ficam de fora', () => {
  const out = colorItems(
    [
      { id: 'c1', numero: '2', nome: ' Azul ', imagem: 'a.png' },
      { id: null, numero: '3', nome: '', imagem: 'b.png' },
      { id: null, numero: '', nome: 'vazia', imagem: '' },
    ],
    { visible: true, newId },
  )
  assert.deepEqual(out, [
    { id: 'c1', numero: 2, nome: 'Azul', imagem: 'a.png', visibilidade: true },
    { id: 'novo-1', numero: 3, nome: '', imagem: 'b.png', visibilidade: true },
  ])
})

test('cores: sem imagem e sem nenhuma linha (ao publicar) são recusadas antes de enviar', () => {
  assert.throws(() => colorItems([{ numero: '4', imagem: '' }], { newId }), /Cor nº 4: escolha uma imagem/)
  assert.throws(() => colorItems([{ numero: '', imagem: '' }], { requireRows: true, newId }), /pelo menos uma cor/)
  assert.deepEqual(colorItems([], { newId }), [])
})

test('produtos: EAN de 13 dígitos, atributo da família e obrigatoriedade', () => {
  const field = { name: 'dimensoes', label: 'Dimensões', required: true }
  assert.deepEqual(variantItems([{ id: 'v1', ean: ' 4006381333931 ', extra: '45x45' }], { extraField: field, newId }), [
    { id: 'v1', ean: '4006381333931', attributes: { dimensoes: '45x45' }, visibilidade: false },
  ])
  assert.throws(() => variantItems([{ ean: '123', extra: 'x' }], { extraField: field, newId }), /13 dígitos/)
  assert.throws(() => variantItems([{ ean: '4006381333931', extra: ' ' }], { extraField: field, newId }), /indique dimensões/)
  assert.throws(() => variantItems([], { requireRows: true, newId }), /pelo menos um produto/)
  // Sem cor ou sem EAN o modelo novo fica como rascunho: o ecrã reconhece estes dois erros.
  assert.throws(() => variantItems([], { requireRows: true, newId }), (e) => e.missingRows === true)
  assert.throws(() => colorItems([], { requireRows: true, newId }), (e) => e.missingRows === true)
  assert.throws(() => variantItems([{ ean: '123' }], { newId }), (e) => !e.missingRows)
  assert.deepEqual(variantItems([{ ean: '4006381333931' }], { newId })[0].attributes, {})
})

test('corpo: o que o utilizador tirou da lista vai nas listas de apagar', () => {
  const body = bundleBody({ model: { nome: 'A' }, colors: [], variants: [], deleteColors: ['c9'], deleteVariants: ['v9'] })
  assert.deepEqual(body, { model: { nome: 'A' }, colors: [], variants: [], delete_colors: ['c9'], delete_variants: ['v9'] })
})
