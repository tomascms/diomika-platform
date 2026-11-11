import { test } from 'node:test'
import assert from 'node:assert/strict'
import { ANNEX_I_FIBRES, isAnnexIFibre, nonAnnexIFibres } from './fibres.js'

// A tabela do Anexo I como o Jornal Oficial a escreve (texto português, L 272, 18.10.2011, mais as linhas 49 e 50 dos
// Regulamentos Delegados 286/2012 e 2018/122), escrita à parte do módulo: se este se enganar, o teste apanha.
const ANNEX_I = [
  [1, 'lã'],
  [2, 'alpaca'],
  [2, 'lama'],
  [2, 'camelo'],
  [2, 'caxemira'],
  [2, 'mohair'],
  [2, 'angorá'],
  [2, 'vicunha'],
  [2, 'iaque'],
  [2, 'guanaco'],
  [2, 'caxegorá'],
  [2, 'castor'],
  [2, 'lontra'],
  [3, 'pêlo'],
  [3, 'crina'],
  [4, 'seda'],
  [5, 'algodão'],
  [6, 'sumaúma'],
  [7, 'linho'],
  [8, 'cânhamo'],
  [9, 'juta'],
  [10, 'abacá'],
  [11, 'alfa'],
  [12, 'coco'],
  [13, 'giesta'],
  [14, 'ramie'],
  [15, 'sisal'],
  [16, 'sunn'],
  [17, 'henequen'],
  [18, 'maguey'],
  [19, 'acetato'],
  [20, 'alginato'],
  [21, 'cupro'],
  [22, 'modal'],
  [23, 'proteínas'],
  [24, 'triacetato'],
  [25, 'viscose'],
  [26, 'acrílica'],
  [27, 'clorofibra'],
  [28, 'fluorofibra'],
  [29, 'modacrílica'],
  [30, 'poliamida ou nylon'],
  [30, 'poliamida'],
  [30, 'nylon'],
  [31, 'aramida'],
  [32, 'poliimida'],
  [33, 'liocel'],
  [34, 'polilactida'],
  [35, 'poliéster'],
  [36, 'polietileno'],
  [37, 'polipropileno'],
  [38, 'policarbamida'],
  [39, 'poliuretano'],
  [40, 'vinilal'],
  [41, 'trivinil'],
  [42, 'elastodieno'],
  [43, 'elastano'],
  [44, 'fibra de vidro'],
  [45, 'elastomultiéster'],
  [46, 'elastolefina'],
  [47, 'melamina'],
  [48, 'metal'],
  [48, 'metálica'],
  [48, 'metalizada'],
  [48, 'amianto'],
  [48, 'papel'],
  [49, 'polipropileno/poliamida bicomponente'],
  [50, 'poliacrilato'],
]

test('«poliéster» e «Algodão» são fibras do Anexo I; «Veludo» não é', () => {
  assert.equal(isAnnexIFibre('poliéster'), true)
  assert.equal(isAnnexIFibre('Algodão'), true)
  assert.equal(isAnnexIFibre('Veludo'), false)
})

test('todas as denominações do Anexo I (linhas 1 a 50) são aceites', () => {
  for (const [row, name] of ANNEX_I)
    assert.equal(isAnnexIFibre(name), true, `linha ${row}: ${name}`)
  // E o módulo não tem mais nem menos do que a tabela.
  const listed = [...ANNEX_I_FIBRES].map((name) => name.normalize('NFC')).toSorted()
  assert.deepEqual(listed, ANNEX_I.map(([, name]) => name.normalize('NFC')).toSorted())
  assert.equal(new Set(ANNEX_I.map(([row]) => row)).size, 50)
})

test('sem acentos nem maiúsculas, e com espaços a mais', () => {
  for (const name of [
    'POLIESTER',
    'poliester',
    ' Poliéster ',
    'ALGODAO',
    'Algodao',
    'liocel',
    'Caxemira',
    'CAXEGORÁ',
    'poliamida  ou   NYLON',
  ]) {
    assert.equal(isAnnexIFibre(name), true, name)
  }
})

test('a linha 2 «precedido ou não de lã ou pêlo», a linha 3 com a espécie e a linha 48 com «fio» ou «fibra»', () => {
  for (const name of [
    'lã de alpaca',
    'Lã Alpaca',
    'pêlo de camelo',
    'pelo de vicunha',
    'Pêlo de bovino',
    'pêlo de cabra comum',
    'crina de cavalo',
    'fio de metal',
    'fibra metálica',
    'fibra metalizada',
    'fibra de papel',
  ]) {
    assert.equal(isAnnexIFibre(name), true, name)
  }
})

test('o que não é fibra, é marca, está noutra língua ou leva um qualificativo, não é', () => {
  for (const name of [
    'Veludo', // o tecido
    'malha',
    'microfibra',
    'Lycra', // marca
    'spandex',
    'polyester', // em inglês
    'cotton',
    'PVC',
    'poliéster reciclado',
    'algodão orgânico',
    'lã virgem',
    'capoque', // a denominação oficial é «sumaúma»
    'lyocell', // «liocel»
    'rami', // «ramie»
    'lã de',
    'fibra',
    'fio',
    'pêlo de',
    '',
    '   ',
    null,
    undefined,
  ]) {
    assert.equal(isAnnexIFibre(name), false, String(name))
  }
})

test('nonAnnexIFibres: do que se escreveu na composição, só o que não é do Anexo I, sem repetir', () => {
  assert.deepEqual(nonAnnexIFibres({ Veludo: 100 }), ['Veludo'])
  assert.deepEqual(nonAnnexIFibres({ Poliester: 80, algodão: 20 }), [])
  assert.deepEqual(nonAnnexIFibres({ ' Poliéster ': 60, Veludo: 30, malha: 10 }), [
    'Veludo',
    'malha',
  ])
  assert.deepEqual(nonAnnexIFibres(['Veludo', 'veludo', 'Algodão', '']), ['Veludo', 'veludo'])
  assert.deepEqual(nonAnnexIFibres({}), [])
  assert.deepEqual(nonAnnexIFibres(null), [])
})
