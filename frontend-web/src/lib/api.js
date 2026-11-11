import { fieldErrors } from '@/lib/errors'

const prodBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')

if (!import.meta.env.DEV && !prodBase) {
  throw new Error('VITE_API_BASE_URL em falta — configure antes do build de produção.')
}

// POST (formulários) vão directos à API. GET de catálogo vão a /api no próprio
// domínio da loja: em produção é a função da Cloudflare (functions/api) que os
// serve da cache do PoP; em dev é o proxy do Vite.
const base = import.meta.env.DEV ? '/api' : prodBase
const getBase = import.meta.env.VITE_EDGE_API === '0' && !import.meta.env.DEV ? prodBase : '/api'

export const API_BASE_URL = base

const DEFAULT_TIMEOUT_MS = 25000

// Sem resposta (rede em baixo, servidor parado ou lento): a culpa não é do visitante nem se lhe pede que «verifique a internet».
const NETWORK_ERROR_MESSAGE = 'O nosso servidor não respondeu. Tente de novo daqui a pouco.'
const TIMEOUT_MESSAGE = 'O nosso servidor não respondeu a tempo. Tente de novo.'

/**
 * Erro de um pedido à API. `status`: o código HTTP (0 se não houve resposta); `network`: não houve resposta
 * (rede ou tempo esgotado: `timeout`); `fields`: num 422, {campo: mensagem em português} (lib/errors.js).
 */
export class ApiError extends Error {
  constructor(message, { status = 0, network = false, timeout = false, fields = {}, cause } = {}) {
    super(message, cause ? { cause } : undefined)
    this.name = 'ApiError'
    this.status = status
    this.network = network
    this.timeout = timeout
    this.fields = fields
  }
}

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
      throw new ApiError(TIMEOUT_MESSAGE, { network: true, timeout: true, cause: err })
    }
    // fetch() rejeita com TypeError («Failed to fetch») quando não há rede.
    if (err instanceof TypeError)
      throw new ApiError(NETWORK_ERROR_MESSAGE, { network: true, cause: err })
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
      if (!err.timeout && attempt < retries) {
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
    throw new ApiError(parseApiDetail(body, resp.status, resp.headers.get('X-Request-Id') || ''), {
      status: resp.status,
      fields: fieldErrors(body),
    })
  }
}

export async function apiPost(path, body, options = {}) {
  const { apiKey = null, idempotencyKey = null, timeoutMs = DEFAULT_TIMEOUT_MS } = options
  const headers = requestHeaders(true)
  if (apiKey) headers['X-API-Key'] = apiKey
  if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey

  let resp
  try {
    resp = await fetchWithTimeout(
      `${base}${path}`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      },
      timeoutMs,
    )
  } catch (err) {
    throw err instanceof ApiError
      ? err
      : new ApiError(NETWORK_ERROR_MESSAGE, { network: true, cause: err })
  }

  const requestId = resp.headers.get('X-Request-Id') || headers['X-Request-Id']
  if (!resp.ok) {
    const errorBody = await resp.json().catch(() => ({}))
    throw new ApiError(parseApiDetail(errorBody, resp.status, requestId), {
      status: resp.status,
      fields: fieldErrors(errorBody),
    })
  }
  return resp.json()
}
