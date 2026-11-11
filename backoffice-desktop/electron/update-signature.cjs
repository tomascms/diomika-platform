/**
 * Verificação do manifesto de actualização (SEG-16): o `latest*.yml` tem de trazer uma assinatura Ed25519 válida
 * e descrever o instalador que o electron-updater descarregou (mesma versão, mesmos sha512).
 * Sem Electron aqui dentro, para se testar com `node --test`.
 */
const crypto = require('node:crypto')

/** `manifest` e `signatureB64` tal como estão no feed; `publicKeyPem` é a chave embutida. Nunca lança. */
function verifyManifest(manifest, signatureB64, publicKeyPem) {
  try {
    const signature = Buffer.from(String(signatureB64 || '').trim(), 'base64')
    if (signature.length !== 64) return false
    return crypto.verify(null, Buffer.from(manifest), crypto.createPublicKey(publicKeyPem), signature)
  } catch {
    return false
  }
}

/** O instalador descarregado (`info` do evento update-downloaded) é o que o manifesto assinado descreve. */
function manifestDescribes(manifest, info) {
  const text = Buffer.from(manifest).toString('utf8')
  const version = (text.match(/^version:\s*(\S+)/m) || [])[1]
  if (!info || !version || version !== String(info.version)) return false
  const hashes = [info.sha512, ...(info.files || []).map((f) => f && f.sha512)].filter(Boolean)
  return hashes.length > 0 && hashes.every((h) => text.includes(h))
}

module.exports = { verifyManifest, manifestDescribes }
