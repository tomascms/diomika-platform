import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  callCostNote,
  COMPANY,
  MAP_URL,
  MIN_ORCAMENTO_MSG,
  MIN_ORDER,
  PRICE_NOTE,
  SELLS_TO_LINE,
} from './constants.js'

const FIXA = 'Chamada para a rede fixa nacional'
const MOVEL = 'Chamada para a rede móvel nacional'
// Os espaços não separáveis (que impedem «500 €» de se partir) comparam-se como espaços.
const plain = (text) => text.replaceAll('\u00a0', ' ')

test('callCostNote: 2… é rede fixa e 9… é rede móvel, no formato do site e no internacional', () => {
  assert.equal(callCostNote('253 422 410'), FIXA)
  assert.equal(callCostNote('+351253422410'), FIXA)
  assert.equal(callCostNote('935 745 663'), MOVEL)
  assert.equal(callCostNote('+351935745663'), MOVEL)
})

test('callCostNote: outros números, ou nada, ficam sem nota (não se adivinha o preço)', () => {
  for (const phone of ['808 200 000', '707 123 456', '', undefined, null]) {
    assert.equal(callCostNote(phone), '', String(phone))
  }
})

// LEGAL-11 e RP-15: as frases da auditoria, à letra. Se uma mudar por engano, o teste reprova.
test('encomenda mínima: 500 € + IVA com o valor com IVA a 23 %, em todo o sítio onde se mostra', () => {
  assert.equal(plain(MIN_ORDER), '500 € + IVA (615 € com IVA a 23 %)')
  assert.ok(plain(MIN_ORCAMENTO_MSG).includes(`Mínimo de encomenda: ${plain(MIN_ORDER)}.`))
})

test('RP-15: a linha de quem compra diz lojas, hotelaria e particulares com o mesmo mínimo', () => {
  assert.equal(
    plain(SELLS_TO_LINE),
    'Vendemos a lojas, hotelaria e particulares — pedido mínimo 500 € + IVA (615 € com IVA a 23 %).',
  )
})

test('LEGAL-11: a particulares a proposta traz sempre o preço total com IVA e portes', () => {
  assert.match(PRICE_NOTE, /sobretudo a revendedores/)
  assert.match(
    PRICE_NOTE,
    /a particulares, a proposta indica sempre o preço total com IVA e portes\.$/,
  )
})

// RP-09: só uma ligação ao mapa (nada de mapa de terceiros incorporado), com a morada da sede.
test('MAP_URL: pesquisa a morada da sede no mapa', () => {
  const url = new URL(MAP_URL)
  assert.equal(url.origin, 'https://www.google.com')
  assert.equal(
    url.searchParams.get('query'),
    `${COMPANY.address}, ${COMPANY.postal}, ${COMPANY.municipality}`,
  )
  assert.equal(
    url.searchParams.get('query'),
    'Rua da Quintã, n.º 89, 4805-116 Caldas das Taipas, Guimarães',
  )
})
