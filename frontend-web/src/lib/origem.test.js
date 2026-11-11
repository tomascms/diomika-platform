import test from 'node:test'
import assert from 'node:assert/strict'
import { entryOrigem, noteVisit, readOrigem } from './origem.js'
import { sessionStore } from './storage.js'

test('entryOrigem: caminho sem query, domínio externo e UTM', () => {
  assert.deepEqual(
    entryOrigem({
      pathname: '/categoria/almofadas',
      search: '?utm_source=google&utm_medium=cpc&email=a@b.pt',
      referrer: 'https://www.google.com/search?q=almofadas',
      ownHost: 'www.diomika.com',
    }),
    {
      entrada: '/categoria/almofadas',
      referrer: 'www.google.com',
      utm_source: 'google',
      utm_medium: 'cpc',
    },
  )
})

test('entryOrigem: referrer do próprio site (com ou sem www) e sem referrer não contam', () => {
  assert.deepEqual(
    entryOrigem({ pathname: '/', referrer: 'https://diomika.com/x', ownHost: 'www.diomika.com' }),
    { entrada: '/' },
  )
  assert.deepEqual(entryOrigem({ pathname: '/contacto', referrer: '' }), { entrada: '/contacto' })
})

test('entryOrigem: valores compridos são cortados', () => {
  assert.equal(
    entryOrigem({ pathname: '/', search: `?utm_source=${'a'.repeat(500)}` }).utm_source.length,
    120,
  )
})

test('noteVisit: a entrada fica a da primeira página e o último modelo vai mudando', () => {
  const loc = { pathname: '/', search: '', hostname: 'www.diomika.com' }
  noteVisit({ loc, referrer: '', routeName: 'home', params: {}, allowed: true })
  noteVisit({
    loc: { ...loc, pathname: '/categoria/a/b' },
    referrer: '',
    routeName: 'product-detail',
    params: { modelSlug: 'modelo-a' },
    allowed: true,
  })
  const last = noteVisit({
    loc: { ...loc, pathname: '/categoria/a/c' },
    referrer: '',
    routeName: 'product-detail',
    params: { modelSlug: 'modelo-b' },
    allowed: true,
  })
  assert.deepEqual(last, { entrada: '/', produto: 'modelo-b' })
  assert.deepEqual(readOrigem(true), last)
})

test('sem consentimento: nada se guarda, nada se devolve e o que havia apaga-se', () => {
  const loc = { pathname: '/', search: '?utm_source=x', hostname: 'www.diomika.com' }
  noteVisit({ loc, referrer: '', routeName: 'home', params: {}, allowed: true })
  assert.ok(sessionStore.get('diomika-origem'))
  assert.equal(readOrigem(false), null)
  assert.equal(sessionStore.get('diomika-origem'), null)
  assert.equal(
    noteVisit({ loc, referrer: '', routeName: 'home', params: {}, allowed: false }),
    null,
  )
  assert.equal(sessionStore.get('diomika-origem'), null)
})
