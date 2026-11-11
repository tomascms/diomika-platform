/**
 * De onde veio quem pede um orçamento (RP-10): página de entrada, domínio de referência, UTM e último modelo visto.
 * Fica no `sessionStorage` e segue no formulário, mas SÓ com o consentimento de analytics: a atribuição (referrer,
 * UTM) não é estritamente necessária para enviar um pedido (Lei 41/2004, art. 5.º; EDPB 2/2023). Sem consentimento
 * nada se guarda, nada se envia e o que lá estava apaga-se. A API só guarda as
 * chaves conhecidas e corta a query (backend-api/core/origem.py). Sem dados pessoais e sem identificadores.
 */
import { sessionStore } from './storage.js'

export const ORIGEM_KEY = 'diomika-origem'
const MAX = 120

const clip = (value) =>
  String(value ?? '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, MAX)

/** A origem de uma primeira visita. `referrer` é o `document.referrer`; só interessa o domínio e se não é o próprio site. */
export function entryOrigem({ pathname = '/', search = '', referrer = '', ownHost = '' } = {}) {
  const out = { entrada: clip(pathname) || '/' }
  try {
    const host = new URL(referrer).hostname
    const same = (a, b) => a.replace(/^www\./, '') === b.replace(/^www\./, '')
    if (host && !(ownHost && same(host, ownHost))) out.referrer = clip(host)
  } catch {
    /* sem referrer válido */
  }
  const params = new URLSearchParams(search)
  for (const key of ['utm_source', 'utm_medium', 'utm_campaign']) {
    const value = clip(params.get(key))
    if (value) out[key] = value
  }
  return out
}

function clearOrigem() {
  sessionStore.remove(ORIGEM_KEY)
}

/** `allowed`: há consentimento de analytics agora. Sem ele devolve `null` e apaga o que houvesse. */
export function readOrigem(allowed) {
  if (!allowed) {
    clearOrigem()
    return null
  }
  try {
    const parsed = JSON.parse(sessionStore.get(ORIGEM_KEY) || 'null')
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

/** Regista a primeira página da sessão e, em cada modelo visto, o último. `loc` é `window.location`. */
export function noteVisit({ loc, referrer, routeName, params, allowed }) {
  let origem = readOrigem(allowed)
  if (!allowed) return null
  if (!origem)
    origem = entryOrigem({
      pathname: loc.pathname,
      search: loc.search,
      referrer,
      ownHost: loc.hostname,
    })
  if (routeName === 'product-detail' && params?.modelSlug)
    origem = { ...origem, produto: clip(params.modelSlug) }
  sessionStore.set(ORIGEM_KEY, JSON.stringify(origem))
  return origem
}
