import { test } from 'node:test'
import assert from 'node:assert/strict'
import { ean13Bits, ean13Check, ean13Svg, validEan13 } from './ean13Svg.js'

test('dígito de controlo: 4006381333931 é o exemplo da norma', () => {
  assert.equal(ean13Check('400638133393'), '1')
  assert.equal(validEan13('4006381333931'), '4006381333931')
  assert.equal(validEan13('4006381333932'), null)
  assert.equal(validEan13('123'), null)
})

test('sequência de 95 módulos com as guardas certas', () => {
  const bits = ean13Bits('4006381333931')
  assert.equal(bits.length, 95)
  assert.ok(bits.startsWith('101') && bits.endsWith('101') && bits.slice(45, 50) === '01010')
  // o primeiro dígito 4 usa o padrão LGLLGG: o segundo dígito (0) é L → 0001101
  assert.equal(bits.slice(3, 10), '0001101')
})

test('SVG vetorial, com as 13 cifras e o EAN no aria-label', () => {
  const svg = ean13Svg('6999030008008')
  assert.ok(svg.startsWith('<svg'))
  assert.ok(svg.includes('viewBox="0 0 113 79"'))
  assert.ok(svg.includes('aria-label="EAN 6999030008008"'))
  assert.equal((svg.match(/<text /g) || []).length, 13)
  assert.ok((svg.match(/<rect /g) || []).length > 20)
})

test('EAN inválido não gera código', () => {
  assert.equal(ean13Svg('6999030008009'), null)
  assert.throws(() => ean13Bits('123'), /EAN inválido/)
})
