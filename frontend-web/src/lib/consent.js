/**
 * Escolha do visitante sobre os cookies de analytics (LEGAL-07; RGPD art. 7.º; Lei 41/2004, art. 5.º).
 * Guarda estado, versão e data, para poder provar o consentimento (art. 7.º/1) e para voltar a perguntar
 * quando a política muda ou ao fim de 12 meses. A lista de cookies está em `CookiesView.vue`.
 */
export const CONSENT_KEY = 'diomika_cookie_consent'

/** Muda sempre que a política de cookies ou a lista de analytics muda: quem escolheu antes é perguntado de novo. */
export const CONSENT_VERSION = '2026-11-02'

const MAX_AGE_MS = 365 * 24 * 60 * 60 * 1000 // 12 meses; a política de cookies diz o mesmo

const STATES = ['accepted', 'rejected']

/** A escolha em vigor, `'accepted'` ou `'rejected'`, ou `null` se é para perguntar (nenhuma, expirada, de outra versão, ilegível). */
export function readConsent(storage, now = Date.now()) {
  let raw
  try {
    // `localStorage` só aqui dentro: com os dados do site bloqueados, até aceder-lhe lança.
    const store = storage ?? localStorage
    raw = store.getItem(CONSENT_KEY)
  } catch {
    return null
  }
  // Valores antigos eram só texto: uma recusa mantém-se (não se trata nada); um «accepted» sem data nem
  // versão não prova o consentimento (e a política mudou), por isso pergunta-se de novo.
  if (raw === 'rejected') return raw
  try {
    const { state, version, date } = JSON.parse(raw)
    const fresh = now - Date.parse(date) < MAX_AGE_MS // data ilegível: NaN, não é fresca
    return STATES.includes(state) && version === CONSENT_VERSION && fresh ? state : null
  } catch {
    return null
  }
}

/** Guarda a escolha com a versão e a data de agora. Sem armazenamento vale só até fechar a página. */
export function saveConsent(state, storage, now = Date.now()) {
  try {
    const store = storage ?? localStorage
    const date = new Date(now).toISOString()
    store.setItem(CONSENT_KEY, JSON.stringify({ state, version: CONSENT_VERSION, date }))
  } catch {
    /* modo privado ou armazenamento bloqueado */
  }
  return state
}
