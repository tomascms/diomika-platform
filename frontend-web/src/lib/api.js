const prodBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')

if (!import.meta.env.DEV && !prodBase) {
  throw new Error('VITE_API_BASE_URL em falta — configure antes do build de produção.')
}

// POST (formulários) vão directos à API. GET de catálogo vão a /api no próprio
// domínio da loja: em produção é a função da Cloudflare (functions/api) que os
// serve da cache do PoP; em dev é o proxy do Vite.
const base = (import.meta.env.DEV ? '/api' : prodBase)
const getBase = import.meta.env.VITE_EDGE_API === '0' && !import.meta.env.DEV ? prodBase : '/api'

export const API_BASE_URL = base

const DEFAULT_TIMEOUT_MS = 25000

const NETWORK_ERROR_MESSAGE = 'Sem ligação ao servidor. Verifique a internet e tente de novo.'

function newRequestId() {
  try {
    return crypto.randomUUID()
  } catch {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
  }
}

/**
 * Cabeçalhos dos POST. Os GET vão sem cabeçalhos próprios de propósito: assim
 * são «simple requests» de CORS e o browser não manda um OPTIONS antes de cada
 * URL novo — eram duas idas ao servidor por página em vez de uma.
 */
function requestHeaders(json = true) {
  const h = {}
  if (json) h['Content-Type'] = 'application/json'
  h['X-Request-Id'] = newRequestId()
  return h
}

export function parseApiDetail(body, status, requestId) {
  if (!body || typeof body !== 'object') {
    return requestId ? `Erro HTTP ${status} (ref: ${requestId.slice(0, 8)})` : `Erro HTTP ${status}`
  }
  const detail = body.detail ?? body.message
  if (typeof detail === 'string') {
    return requestId ? `${detail} (ref: ${requestId.slice(0, 8)})` : detail
  }
  if (Array.isArray(detail)) {
    const msg = detail.map((item) => item.msg || item.message || JSON.stringify(item)).join(' · ')
    return requestId ? `${msg} (ref: ${requestId.slice(0, 8)})` : msg
  }
  if (detail && typeof detail === 'object') {
    const msg = detail.msg || detail.message || JSON.stringify(detail)
    return requestId ? `${msg} (ref: ${requestId.slice(0, 8)})` : msg
  }
  return requestId ? `Erro HTTP ${status} (ref: ${requestId.slice(0, 8)})` : `Erro HTTP ${status}`
}

async function fetchWithTimeout(url, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, { ...options, signal: controller.signal })
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('O servidor demorou demasiado a responder. Tente novamente.', { cause: err })
    }
    // fetch() rejeita com TypeError («Failed to fetch») quando não há rede.
    if (err instanceof TypeError) throw new Error(NETWORK_ERROR_MESSAGE, { cause: err })
    throw err
  } finally {
    clearTimeout(timer)
  }
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

const RETRYABLE_STATUS = new Set([502, 503, 504])

/** GET com repetição (backoff) só em falhas transitórias: sem rede ou 502/503/504. */
export async function apiGet(path, { retries = 2 } = {}) {
  for (let attempt = 0; ; attempt += 1) {
    let resp
    try {
      resp = await fetchWithTimeout(`${getBase}${path}`)
    } catch (err) {
      // Um timeout (25 s) não se repete — só falhas rápidas de rede.
      const timedOut = String(err?.message || '').includes('demorou')
      if (!timedOut && attempt < retries) {
        await sleep(300 * 2 ** attempt)
        continue
      }
      throw err
    }
    if (resp.ok) return resp.json()
    if (RETRYABLE_STATUS.has(resp.status) && attempt < retries) {
      await sleep(300 * 2 ** attempt)
      continue
    }
    const body = await resp.json().catch(() => ({}))
    const error = new Error(parseApiDetail(body, resp.status, resp.headers.get('X-Request-Id') || ''))
    error.status = resp.status
    throw error
  }
}

export async function apiPost(path, body, options = {}) {
  const { apiKey = null, idempotencyKey = null, timeoutMs = DEFAULT_TIMEOUT_MS } = options
  const headers = requestHeaders(true)
  if (apiKey) headers['X-API-Key'] = apiKey
  if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey

  let resp
  try {
    resp = await fetchWithTimeout(`${base}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    }, timeoutMs)
  } catch (err) {
    if (err.message?.includes('demasiado')) throw err
    throw new Error(NETWORK_ERROR_MESSAGE, { cause: err })
  }

  const requestId = resp.headers.get('X-Request-Id') || headers['X-Request-Id']
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    throw new Error(parseApiDetail(err, resp.status, requestId))
  }
  return resp.json()
}
