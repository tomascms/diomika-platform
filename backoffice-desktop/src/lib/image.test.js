import test from 'node:test'
import assert from 'node:assert/strict'
import { imageWarnings } from './image.js'

test('foto quadrada e grande: sem avisos', () => {
  assert.deepEqual(imageWarnings(1600, 1600), [])
  assert.deepEqual(imageWarnings(1500, 1300), [])
})

test('foto pequena: avisa da resolução', () => {
  const [w] = imageWarnings(800, 800)
  assert.match(w, /Imagem pequena \(800×800\)/)
})

test('foto comprida: avisa do recorte; pequena e comprida dá os dois avisos', () => {
  assert.equal(imageWarnings(2400, 1200).length, 1)
  assert.match(imageWarnings(2400, 1200)[0], /quadrado/)
  assert.equal(imageWarnings(1000, 400).length, 2)
})

test('sem dimensões (imagem que não abriu): nada a dizer', () => {
  assert.deepEqual(imageWarnings(0, 0), [])
})
