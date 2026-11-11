import { test } from 'node:test'
import assert from 'node:assert/strict'
import { productWhatsAppMessage } from './whatsappMessage.js'

const URL = 'https://www.diomika.com/categoria/almofada/foglia'

test('o modelo, a categoria, a cor, a medida, o EAN e o endereço', () => {
  assert.equal(
    productWhatsAppMessage({
      name: 'Foglia',
      category: 'Almofada',
      colour: 'Azul Ciano',
      measureNoun: 'medida',
      measure: '45x45 cm',
      ean: '5606044506574',
      url: URL,
    }),
    `Olá! Gostaria de saber mais sobre o modelo Foglia (Almofada), cor Azul Ciano, medida 45x45 cm, EAN 5606044506574. ${URL}`,
  )
})

test('o que o modelo não tem, não aparece: sem cor escolhida, sem medida (artigo único), sem categoria', () => {
  assert.equal(
    productWhatsAppMessage({ name: 'Adulto', category: 'Óculos', ean: '5606044800011', url: URL }),
    `Olá! Gostaria de saber mais sobre o modelo Adulto (Óculos), EAN 5606044800011. ${URL}`,
  )
  assert.equal(
    productWhatsAppMessage({ name: 'Adulto', url: URL }),
    `Olá! Gostaria de saber mais sobre o modelo Adulto. ${URL}`,
  )
})

test('uma altura de assento diz «altura», não «medida»', () => {
  assert.match(
    productWhatsAppMessage({
      name: 'Liso',
      category: 'Assento',
      measureNoun: 'altura',
      measure: '32mm',
      url: URL,
    }),
    /, altura 32mm\. /,
  )
})
