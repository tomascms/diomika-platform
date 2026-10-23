/** Backoffice — sessão + proxy same-origin /api → API cloud (Electron). */
const STORAGE_KEY = 'diomika-backoffice-settings'
const SESSION_TOKEN_KEY = 'diomika-backoffice-session-token'
const SESSION_USER_KEY = 'diomika-backoffice-session-user'
const LEGACY_API_KEY = 'diomika-backoffice-session'

const DEV_API_KEY =
  typeof __DIOMIKA_DEV_API_KEY__ !== 'undefined' ? __DIOMIKA_DEV_API_KEY__ : ''

const LOCAL_API_BASE = '/api'

function readStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

// «Manter sessão iniciada»: token em localStorage (sobrevive a fechar a app;
// o servidor expira-o ao fim de ADMIN_SESSION_TTL — 7 dias, ou 12 h sem uso, por omissão).
// Sem isso fica em sessionStorage e morre com a janela.
function sessionStores() {
  const stores = []
  try { stores.push(sessionStorage) } catch { /* ignore */ }
  try { stores.push(localStorage) } catch { /* ignore */ }
  return stores
}

function readFirst(key) {
  for (const store of sessionStores()) {
    try {
      const v = store.getItem(key)
      if (v) return v
    } catch {
      /* ignore */
    }
  }
  return ''
}

function removeEverywhere(key) {
  for (const store of sessionStores()) {
    try { store.removeItem(key) } catch { /* ignore */ }
  }
}

export function readSessionToken() {
  return readFirst(SESSION_TOKEN_KEY)
}

export function writeSessionToken(token, { remember = false } = {}) {
  removeEverywhere(SESSION_TOKEN_KEY)
  if (!token) return
  try {
    ;(remember ? localStorage : sessionStorage).setItem(SESSION_TOKEN_KEY, token)
  } catch {
    /* ignore */
  }
}

export function readSessionUser() {
  try {
    const raw = readFirst(SESSION_USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function writeSessionUser(user, { remember = false } = {}) {
  removeEverywhere(SESSION_USER_KEY)
  if (!user) return
  try {
    ;(remember ? localStorage : sessionStorage).setItem(SESSION_USER_KEY, JSON.stringify(user))
  } catch {
    /* ignore */
  }
}

/** Guarda a sessão emitida pelo login (token + utilizador) de uma vez. */
export function storeSession({ token, user, remember = false }) {
  writeSessionToken(token, { remember })
  writeSessionUser(user, { remember })
}

function readLegacyApiKey() {
  try {
    return sessionStorage.getItem(LEGACY_API_KEY) || ''
  } catch {
    return ''
  }
}

export function defaultSettings() {
  return {
    apiBaseUrl: LOCAL_API_BASE,
    apiKey: '',
    accessToken: '',
  }
}

export function isRemoteApiUrl(url) {
  const u = (url || '').trim().toLowerCase()
  if (!u || u.startsWith('/api')) return false
  return !u.includes('127.0.0.1') && !u.includes('localhost')
}

export function loadSettings() {
  try {
    const saved = readStorage()
    const defaults = defaultSettings()
    const token = readSessionToken()
    const legacyKey = readLegacyApiKey()
    return {
      ...defaults,
      ...saved,
      accessToken: token || '',
      apiKey: token ? '' : (legacyKey || saved.apiKey || (import.meta.env.DEV ? DEV_API_KEY : '') || ''),
      apiBaseUrl: LOCAL_API_BASE,
    }
  } catch {
    return defaultSettings()
  }
}

export function saveSettings(partial) {
  if ('accessToken' in partial) {
    writeSessionToken(partial.accessToken || '')
  }
  if ('apiKey' in partial && !partial.accessToken) {
    try {
      if (partial.apiKey) sessionStorage.setItem(LEGACY_API_KEY, partial.apiKey)
      else sessionStorage.removeItem(LEGACY_API_KEY)
    } catch {
      /* ignore */
    }
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ apiBaseUrl: LOCAL_API_BASE }))
  return loadSettings()
}

export function clearSession() {
  writeSessionToken('')
  writeSessionUser(null)
  try {
    sessionStorage.removeItem(LEGACY_API_KEY)
  } catch {
    /* ignore */
  }
}

export function clearSettings() {
  localStorage.removeItem(STORAGE_KEY)
  clearSession()
  return defaultSettings()
}

export function isAuthenticated() {
  const s = loadSettings()
  return Boolean(s.accessToken?.trim() || s.apiKey?.trim())
}

export function isConfigured() {
  return true
}

export function bootstrapSettings() {
  return saveSettings({ apiBaseUrl: LOCAL_API_BASE })
}

/** Mensagem legível para o utilizador. Aceita um Error (usa o status HTTP) ou texto. */
export function mapApiError(input) {
  const status = typeof input === 'object' && input ? Number(input.status) || 0 : 0
  const msg = String((typeof input === 'object' && input ? input.message : input) || '')
  if (status === 401 || /sess[aã]o (inv[aá]lida|expirada)|api key inv[aá]lida|Erro HTTP 401/i.test(msg)) {
    return 'Sessão expirada. Volte a iniciar sessão.'
  }
  if (status === 429 || /Erro HTTP 429|demasiados pedidos/i.test(msg)) {
    return 'Demasiados pedidos seguidos. Aguarde uns segundos e tente de novo.'
  }
  if (status === 403 || /Erro HTTP 403|localhost na produção|Admin\/system/i.test(msg)) {
    return msg && !/Erro HTTP 403/.test(msg) ? msg : 'Sem permissão para esta operação.'
  }
  if ([502, 503, 504].includes(status) || /Erro HTTP 50[234]|inacessível/i.test(msg)) {
    return 'O servidor não respondeu. Se estava a guardar, confirme na lista antes de repetir.'
  }
  if (/timeout|abort/i.test(msg)) return 'O servidor demorou demasiado a responder. Tente de novo.'
  if (/failed to fetch|network|sem ligação/i.test(msg)) {
    return 'Sem ligação à API. Verifique a internet e tente de novo.'
  }
  if (status >= 500 || /Erro HTTP 500|internal server/i.test(msg)) {
    return 'Erro no servidor. Tente mais tarde ou contacte o suporte Diomika.'
  }
  return msg || 'Erro de ligação.'
}
