import { loadSettings, clearSession, mapApiError } from './settings'

const TIMEOUT_MS = 30000
const WRITE_TIMEOUT_MS = 90000
const CATEGORIES_TTL_MS = 5 * 60 * 1000
const AUTH_STATUS_TTL_MS = 5 * 60 * 1000
const ME_TTL_MS = 10 * 60 * 1000
// Leituras (GET) repetem em falhas transitórias de rede / túnel; escritas nunca
// repetem sozinhas — um POST que chegou ao servidor não pode ser duplicado.
const READ_RETRY_DELAYS_MS = [400, 1200]
const RETRYABLE_STATUS = new Set([502, 503, 504])

/** Disparado quando a API recusa a sessão — o router leva para o login. */
export const UNAUTHORIZED_EVENT = 'diomika:unauthorized'

// Request deduplication — previne múltiplos requests ao mesmo endpoint
const pendingRequests = new Map()

const caches = {
  schema: new Map(),
  relation: new Map(),
  categories: { value: null, at: 0 },
  authStatus: { value: null, at: 0 },
  me: { value: null, at: 0 },
}

/** Erro da API com status HTTP; a mensagem já vem pronta para mostrar ao utilizador. */
export class ApiError extends Error {
  constructor(message, status = 0) {
    super(mapApiError({ message, status }))
    this.name = 'ApiError'
    this.status = status
    this.rawMessage = message
  }
}

export function clearApiCaches() {
  caches.authStatus = { value: null, at: 0 }
  caches.me = { value: null, at: 0 }
  caches.categories = { value: null, at: 0 }
  caches.schema.clear()
  caches.relation.clear()
}

function getCached(store, ttl) {
  return store.value && Date.now() - store.at < ttl ? store.value : null
}

function setCached(store, value) {
  store.value = value
  store.at = Date.now()
  return value
}

function timeoutFor(method) {
  return ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) ? WRITE_TIMEOUT_MS : TIMEOUT_MS
}

function baseUrl() {
  return (loadSettings().apiBaseUrl || '').replace(/\/+$/, '')
}

function headers(json = true) {
  const h = {}
  if (json) h['Content-Type'] = 'application/json'
  const s = loadSettings()
  if (s.accessToken) {
    h.Authorization = `Bearer ${s.accessToken}`
  } else if (s.apiKey) {
    h['X-API-Key'] = s.apiKey
  }
  return h
}

function parseDetail(body, status) {
  if (!body || typeof body !== 'object') return `Erro HTTP ${status}`
  const detail = body.detail ?? body.message
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((i) => i.msg || i.message || JSON.stringify(i)).join(' · ')
  }
  return `Erro HTTP ${status}`
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

function handleUnauthorized(path) {
  // O próprio login devolve 401 em credenciais erradas — isso não é sessão expirada.
  if (path.startsWith('/admin/auth/login') || path.startsWith('/admin/auth/mfa')) return
  clearApiCaches()
  clearSession()
  window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT))
}

async function fetchOnce(method, url, path, { body, headers: extraHeaders }) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutFor(method))
  try {
    let resp
    try {
      resp = await fetch(url, {
        method,
        headers: { ...headers(body !== undefined), ...(extraHeaders || {}) },
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      })
    } catch (err) {
      if (err?.name === 'AbortError') throw new ApiError('Timeout ao contactar a API.', 0)
      throw new ApiError('Sem ligação à API (failed to fetch).', 0)
    }
    if (!resp.ok) {
      if (resp.status === 401) handleUnauthorized(path)
      const err = await resp.json().catch(() => ({}))
      throw new ApiError(parseDetail(err, resp.status), resp.status)
    }
    const text = await resp.text()
    return text ? JSON.parse(text) : {}
  } finally {
    clearTimeout(timer)
  }
}

async function request(method, path, { body, params, headers: extraHeaders } = {}) {
  let url = `${baseUrl()}${path}`
  if (params) url += `?${new URLSearchParams(params)}`

  // Deduplicação: o mesmo GET em curso devolve a mesma promise.
  const dedupeKey = `${method}:${url}`
  if (method === 'GET' && pendingRequests.has(dedupeKey)) {
    return pendingRequests.get(dedupeKey)
  }

  const promise = (async () => {
    try {
      if (method !== 'GET') return await fetchOnce(method, url, path, { body, headers: extraHeaders })
      for (let attempt = 0; ; attempt += 1) {
        try {
          return await fetchOnce(method, url, path, { body, headers: extraHeaders })
        } catch (err) {
          const transient = err.status === 0 || RETRYABLE_STATUS.has(err.status)
          if (!transient || attempt >= READ_RETRY_DELAYS_MS.length) throw err
          await sleep(READ_RETRY_DELAYS_MS[attempt])
        }
      }
    } finally {
      pendingRequests.delete(dedupeKey)
    }
  })()

  if (method === 'GET') pendingRequests.set(dedupeKey, promise)
  return promise
}

async function downloadBlob(path) {
  let resp
  try {
    resp = await fetch(`${baseUrl()}${path}`, { headers: headers(false) })
  } catch {
    throw new ApiError('Sem ligação à API (failed to fetch).', 0)
  }
  if (resp.status === 401) handleUnauthorized(path)
  if (!resp.ok) throw new ApiError(`Erro ao descarregar (${resp.status})`, resp.status)
  return resp.blob()
}

/** POST multipart (upload de imagem / import CSV) com timeout e erros normalizados. */
async function postForm(path, file) {
  const fd = new FormData()
  fd.append('file', file)
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutFor('POST'))
  try {
    let resp
    try {
      resp = await fetch(`${baseUrl()}${path}`, {
        method: 'POST',
        headers: headers(false),
        body: fd,
        signal: controller.signal,
      })
    } catch (err) {
      if (err?.name === 'AbortError') throw new ApiError('Timeout ao enviar o ficheiro.', 0)
      throw new ApiError('Sem ligação à API (failed to fetch).', 0)
    }
    if (!resp.ok) {
      if (resp.status === 401) handleUnauthorized(path)
      const err = await resp.json().catch(() => ({}))
      throw new ApiError(parseDetail(err, resp.status), resp.status)
    }
    return resp.json()
  } finally {
    clearTimeout(timer)
  }
}

function uploadFile(table, field, file) {
  return postForm(
    `/admin/crud/upload-image?table=${encodeURIComponent(table)}&field=${encodeURIComponent(field)}`,
    file,
  )
}

function normalizeMergedPage(data) {
  if (Array.isArray(data)) {
    return { items: data, count: data.length, total_approx: data.length, limit: data.length, offset: 0 }
  }
  const items = data?.items || []
  return {
    items,
    count: data?.count ?? items.length,
    total_approx: data?.total_approx ?? items.length,
    limit: data?.limit,
    offset: data?.offset ?? 0,
  }
}

export const api = {
  get: (path, params) => request('GET', path, { params }),
  post: (path, body) => request('POST', path, { body }),
  put: (path, body) => request('PUT', path, { body }),
  patch: (path, body) => request('PATCH', path, { body }),
  delete: (path, params) => request('DELETE', path, { params }),
  health: () => request('GET', '/health'),
  authStatus: async (force = false) => {
    if (!force) {
      const cached = getCached(caches.authStatus, AUTH_STATUS_TTL_MS)
      if (cached) return cached
    }
    const st = await request('GET', '/admin/auth/status')
    return setCached(caches.authStatus, st)
  },
  login: (username, password, totp_code) =>
    request('POST', '/admin/auth/login', {
      body: totp_code ? { username, password, totp_code } : { username, password },
    }),
  mfaSetup: (username, password) =>
    request('POST', '/admin/auth/mfa/setup', { body: { username, password } }),
  mfaConfirm: (username, password, totp_code) =>
    request('POST', '/admin/auth/mfa/confirm', {
      body: { username, password, totp_code },
    }),
  logout: async () => {
    try {
      return await request('POST', '/admin/auth/logout')
    } finally {
      clearApiCaches()
    }
  },
  me: async (force = false) => {
    if (!force) {
      const cached = getCached(caches.me, ME_TTL_MS)
      if (cached) return cached
    }
    const me = await request('GET', '/admin/auth/me')
    return setCached(caches.me, me)
  },
  workspace: () => request('GET', '/system/workspace'),
  formSchema: (table) => {
    if (caches.schema.has(table)) return caches.schema.get(table)
    const pending = request('GET', `/system/schema/form/${table}`).then((data) => {
      caches.schema.set(table, Promise.resolve(data))
      return data
    })
    caches.schema.set(table, pending)
    return pending
  },
  formBundle: async (table, id = null) => {
    const params = {}
    if (id) params.id = id
    return request('GET', `/admin/form/${table}`, { params })
  },
  listRecords: async (table, params) => {
    const data = await request('GET', `/admin/crud/${table}`, { params })
    return Array.isArray(data) ? data : data?.items || []
  },
  listRecordsPage: async (table, params) => {
    const data = await request('GET', `/admin/crud/${table}`, { params })
    if (Array.isArray(data)) {
      return { items: data, limit: data.length, offset: 0, count: data.length }
    }
    return {
      items: data?.items || [],
      limit: data?.limit,
      offset: data?.offset ?? 0,
      count: data?.count ?? (data?.items || []).length,
    }
  },
  listRelationOptions: async (table, { force = false } = {}) => {
    if (!force && caches.relation.has(table)) return caches.relation.get(table)
    const pending = (async () => {
      try {
        const data = await request('GET', `/admin/crud/${table}/options`, {
          params: { visible_only: 'false', limit: '200' },
        })
        return data?.items || []
      } catch {
        return []
      }
    })()
    caches.relation.set(table, pending)
    return pending
  },
  listCategoriesForForms: async (force = false) => {
    if (!force) {
      const cached = getCached(caches.categories, CATEGORIES_TTL_MS)
      if (cached) return cached
    }
    const data = await request('GET', '/admin/crud/categories/options', {
      params: { visible_only: 'false', limit: '300' },
    })
    const rows = (data?.items || []).map((r) => ({
      id: r.id,
      nome: r.label,
      tipo_catalogo: r.tipo_catalogo || null,
    }))
    const filtered = rows.filter((c) => c.tipo_catalogo)
    return setCached(caches.categories, filtered)
  },
  listModelColors: async (colorsTable, modelId) => {
    if (!colorsTable || !modelId) return []
    const params = {
      id_modelo: modelId,
      visible_only: 'false',
      limit: '200',
    }
    const data = await request('GET', `/admin/crud/${colorsTable}`, { params })
    return Array.isArray(data) ? data : data?.items || []
  },
  publishRecord: (table, id) => request('POST', `/admin/crud/${table}/${id}/publish`),
  setVisibility: (table, id, visibilidade) =>
    request('PATCH', `/admin/crud/${table}/${id}/visibility`, { body: { visibilidade } }),
  setLida: (table, id, lida) =>
    request('PATCH', `/admin/crud/${table}/${id}/lida`, { body: { lida } }),
  getRecord: (table, id) => request('GET', `/admin/crud/${table}/${id}`),
  createRecord: (table, body, idempotencyKey = null) => {
    const opts = { body }
    if (idempotencyKey) {
      opts.headers = { 'Idempotency-Key': idempotencyKey }
    }
    return request('POST', `/admin/crud/${table}`, opts)
  },
  updateRecord: (table, id, body) => request('PUT', `/admin/crud/${table}/${id}`, { body }),
  deleteRecord: (table, id, hard = false) =>
    request('DELETE', `/admin/crud/${table}/${id}`, { params: { hard: String(hard) } }),
  uploadImage: (table, field, file) => uploadFile(table, field, file),
  // Criar categoria é CRUD real: createRecord('categories', {...}) — qualquer
  // nome/imagem, para qualquer família (categoryTipos() alimenta o dropdown
  // de família), sem limite a uma categoria por família.
  categoryTipos: () => request('GET', '/system/categories/tipos'),
  mergedList: async (viewKey, params = {}) => {
    const data = await request('GET', `/catalogo/admin/merged/${viewKey}`, {
      params: { limit: '40', offset: '0', ...params },
    })
    return normalizeMergedPage(data)
  },
  orderPicker: (categoryId) => request('GET', `/system/order-picker/${categoryId}`),
  createOrder: (body) => request('POST', '/encomendas-internas', { body }),
  orderPdf: (id) => downloadBlob(`/encomendas-internas/${id}/pdf`),
  orcamentoPdf: (id) => downloadBlob(`/orcamentos/${id}/pdf`),
  exportCsv: (table) => downloadBlob(`/admin/export/${table}`),
  importCsv: (table, file, dryRun = false) =>
    postForm(`/admin/import/${encodeURIComponent(table)}?dry_run=${dryRun}`, file),
  listContact: async () => {
    const data = await request('GET', '/contacto', { params: { limit: '200', offset: '0' } })
    return Array.isArray(data) ? data : data?.items || []
  },
  getContactMessage: (id) => request('GET', `/contacto/${id}`),
  markContactRead: (id, lida = true) => request('PATCH', `/contacto/${id}/lida?lida=${lida}`),
  listCategories: () => request('GET', '/categorias'),
}
