const test = require('node:test')
const assert = require('node:assert/strict')
const crypto = require('node:crypto')
const { isAppOrigin, hostAllowed } = require('./guards.cjs')
const { verifyManifest, manifestDescribes } = require('./update-signature.cjs')

test('origem: a origem inteira conta, o prefixo não', () => {
  const origin = 'http://127.0.0.1:5174'
  assert.equal(isAppOrigin('http://127.0.0.1:5174/#/workspace/x', origin), true)
  assert.equal(isAppOrigin('http://127.0.0.1.evil.example/', origin), false)
  assert.equal(isAppOrigin('http://127.0.0.1:5175/', origin), false)
  assert.equal(isAppOrigin('https://127.0.0.1:5174/', origin), false)
  assert.equal(isAppOrigin('lixo', origin), false)
  assert.equal(isAppOrigin('http://127.0.0.1:5174/', null), false)
})

test('Host: só 127.0.0.1 ou localhost com a porta certa', () => {
  assert.equal(hostAllowed('127.0.0.1:5174', 5174), true)
  assert.equal(hostAllowed('localhost:5174', 5174), true)
  assert.equal(hostAllowed('evil.example:5174', 5174), false)
  assert.equal(hostAllowed('127.0.0.1:5174.evil.example', 5174), false)
  assert.equal(hostAllowed('127.0.0.1', 5174), false)
  assert.equal(hostAllowed(undefined, 5174), false)
})

const { publicKey, privateKey } = crypto.generateKeyPairSync('ed25519')
const publicPem = publicKey.export({ type: 'spki', format: 'pem' })
const MANIFEST = 'version: 1.4.0\nfiles:\n  - url: Diomika-Backoffice-1.4.0-setup.exe\n    sha512: AbC+/123==\n    size: 10\npath: Diomika-Backoffice-1.4.0-setup.exe\nsha512: AbC+/123==\n'
const sign = (text) => crypto.sign(null, Buffer.from(text), privateKey).toString('base64')

test('assinatura: válida passa; manifesto alterado, outra chave e lixo falham', () => {
  assert.equal(verifyManifest(MANIFEST, sign(MANIFEST), publicPem), true)
  assert.equal(verifyManifest(MANIFEST.replace('1.4.0', '1.9.9'), sign(MANIFEST), publicPem), false)
  const other = crypto.generateKeyPairSync('ed25519').publicKey.export({ type: 'spki', format: 'pem' })
  assert.equal(verifyManifest(MANIFEST, sign(MANIFEST), other), false)
  assert.equal(verifyManifest(MANIFEST, '', publicPem), false)
  assert.equal(verifyManifest(MANIFEST, 'não é base64 de 64 bytes', publicPem), false)
  assert.equal(verifyManifest(MANIFEST, sign(MANIFEST), 'não é uma chave'), false)
})

test('o manifesto assinado descreve o instalador descarregado (versão e sha512)', () => {
  const info = { version: '1.4.0', sha512: 'AbC+/123==', files: [{ url: 'x.exe', sha512: 'AbC+/123==' }] }
  assert.equal(manifestDescribes(MANIFEST, info), true)
  assert.equal(manifestDescribes(MANIFEST, { ...info, version: '1.5.0' }), false)
  assert.equal(manifestDescribes(MANIFEST, { ...info, files: [{ sha512: 'OUTRO==' }] }), false)
  assert.equal(manifestDescribes(MANIFEST, { version: '1.4.0' }), false)
  assert.equal(manifestDescribes(MANIFEST, null), false)
})

test('a chave embutida é uma chave Ed25519 pública', () => {
  const key = crypto.createPublicKey(require('./update-key.cjs'))
  assert.equal(key.asymmetricKeyType, 'ed25519')
})
