import { test } from 'node:test'
import assert from 'node:assert/strict'
import { CONSENT_KEY, CONSENT_VERSION, readConsent, saveConsent } from './consent.js'

const DAY = 24 * 60 * 60 * 1000
const NOW = Date.parse('2027-03-01T10:00:00Z')

/** Armazenamento de mentira: só o que o módulo usa. */
const storage = (initial = {}) => {
  const data = new Map(Object.entries(initial))
  return { getItem: (k) => data.get(k) ?? null, setItem: (k, v) => data.set(k, v) }
}
const stored = (state, { version = CONSENT_VERSION, daysAgo = 1 } = {}) => ({
  [CONSENT_KEY]: JSON.stringify({
    state,
    version,
    date: new Date(NOW - daysAgo * DAY).toISOString(),
  }),
})

test('a escolha guardada guarda estado, versão e data (RGPD art. 7.º/1: poder provar o consentimento)', () => {
  const s = storage()
  assert.equal(saveConsent('accepted', s, NOW), 'accepted')
  assert.deepEqual(JSON.parse(s.getItem(CONSENT_KEY)), {
    state: 'accepted',
    version: CONSENT_VERSION,
    date: '2027-03-01T10:00:00.000Z',
  })
  assert.equal(readConsent(s, NOW), 'accepted')
})

test('sem escolha, ou com valor ilegível, pergunta-se: null', () => {
  assert.equal(readConsent(storage(), NOW), null)
  for (const raw of [
    '',
    'talvez',
    '{',
    '{"state":"accepted"}',
    '{"state":"sim","version":"x","date":"x"}',
  ]) {
    assert.equal(readConsent(storage({ [CONSENT_KEY]: raw }), NOW), null, raw)
  }
})

test('uma recusa e uma aceitação recentes, da versão em vigor, mantêm-se', () => {
  assert.equal(readConsent(storage(stored('rejected')), NOW), 'rejected')
  assert.equal(readConsent(storage(stored('accepted')), NOW), 'accepted')
})

test('quando a política muda (outra versão), pergunta-se de novo', () => {
  assert.equal(readConsent(storage(stored('accepted', { version: 'antiga' })), NOW), null)
  assert.equal(readConsent(storage(stored('rejected', { version: 'antiga' })), NOW), null)
})

test('a escolha vale 12 meses: aos 364 dias mantém-se, aos 366 pergunta-se de novo', () => {
  assert.equal(readConsent(storage(stored('accepted', { daysAgo: 364 })), NOW), 'accepted')
  assert.equal(readConsent(storage(stored('accepted', { daysAgo: 366 })), NOW), null)
  assert.equal(readConsent(storage(stored('rejected', { daysAgo: 366 })), NOW), null)
})

test('valores antigos, só texto: «rejected» mantém-se (nada é tratado), «accepted» não prova nada e pergunta-se de novo', () => {
  assert.equal(readConsent(storage({ [CONSENT_KEY]: 'rejected' }), NOW), 'rejected')
  assert.equal(readConsent(storage({ [CONSENT_KEY]: 'accepted' }), NOW), null)
})

test('sem armazenamento (modo privado, bloqueado): lê null e grava sem rebentar', () => {
  const broken = {
    getItem() {
      throw new Error('bloqueado')
    },
    setItem() {
      throw new Error('bloqueado')
    },
  }
  assert.equal(readConsent(broken, NOW), null)
  assert.equal(saveConsent('rejected', broken, NOW), 'rejected')
})
