import { getImageUrl, storageObjectPath } from '@/lib/supabaseConfig'

export const PLACEHOLDER = '/placeholder.svg'

/**
 * Miniatura gravada pela API no upload (`<ficheiro>.w480.webp`, `.w960.webp`).
 * URL da miniatura para listas e cartões. Só para URLs públicas do Storage
 * (as assinadas não se podem derivar); nos outros casos devolve o próprio URL.
 */
export function thumbUrl(url, width = 480) {
  const value = String(url || '')
  if (!/\/storage\/v1\/object\/public\//.test(value)) return value
  const [path] = value.split('?')
  if (/\.(gif|svg)$/i.test(path) || /\.w\d+\.webp$/.test(path)) return value
  return `${path}.w${width}.webp`
}

/** Presets opcionais (só se VITE_IMAGE_TRANSFORM=1). Por omissão off — mais rápido e fiável. */
export const IMG_THUMB = { width: 640, quality: 72, resize: 'contain' }
export const IMG_CARD = { width: 720, quality: 75, resize: 'contain' }
export const IMG_HERO = { width: 1200, quality: 78, resize: 'contain' }
export const IMG_DETAIL = { width: 1400, quality: 80, resize: 'contain' }

const signedMemo = new Map()
const PERSIST_KEY = 'diomika_signed_v5'
const PERSIST_TTL_MS = 50 * 60 * 1000

function storagePrivateEnabled() {
  return /^(1|true|yes)$/i.test(String(import.meta.env.VITE_STORAGE_PRIVATE || '').trim())
}

function transformEnabled() {
  const raw = String(import.meta.env.VITE_IMAGE_TRANSFORM ?? '0').trim()
  return /^(1|true|yes)$/i.test(raw)
}

function isReadyUrl(value) {
  return (
    typeof value === 'string' &&
    (/^https?:\/\//i.test(value) || value.startsWith('data:') || value.startsWith('/'))
  )
}

function isPlaceholderUrl(value) {
  const v = String(value || '')
  return v === PLACEHOLDER || v.endsWith('/placeholder.svg') || v.includes('placeholder.svg')
}

/**
 * Precisa de signed URL fresca (bucket privado).
 * URLs /object/sign/… gravadas na BD expiram — nunca usar o token antigo.
 */
export function needsPrivateSign(path) {
  if (!path || !storagePrivateEnabled()) return false
  const raw = String(path).trim()
  if (!raw || /^data:/i.test(raw)) return false
  if (isPlaceholderUrl(raw)) return false
  return Boolean(storageObjectPath(raw))
}

function cacheKey(path, transform) {
  const base = storageObjectPath(path) || String(path || '').trim()
  if (!base) return ''
  if (!transform) return base
  return `${base}::w${transform.width || ''}q${transform.quality || ''}`
}

function purgeLegacyCaches() {
  if (typeof sessionStorage === 'undefined') return
  try {
    ;[
      'diomika_signed_v1',
      'diomika_signed_v2',
      'diomika_signed_v3',
      'diomika_signed_v4',
    ].forEach((k) => sessionStorage.removeItem(k))
  } catch {
    /* ignore */
  }
}

purgeLegacyCaches()

function readPersist(key) {
  if (!key || typeof sessionStorage === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(PERSIST_KEY)
    if (!raw) return null
    const bag = JSON.parse(raw)
    const row = bag?.[key]
    if (!row?.url || !row?.exp || Date.now() > row.exp) return null
    if (!isReadyUrl(row.url) || isPlaceholderUrl(row.url)) return null
    // Só aceitar signed frescas em cache — nunca public nem tokens da BD
    if (!/\/object\/sign\//i.test(row.url) && !/\/render\/image\/sign\//i.test(row.url)) {
      return null
    }
    return row.url
  } catch {
    return null
  }
}

function writePersist(key, url) {
  if (!key || !url || typeof sessionStorage === 'undefined') return
  if (!isReadyUrl(url) || isPlaceholderUrl(url)) return
  if (!/\/object\/sign\//i.test(url) && !/\/render\/image\/sign\//i.test(url)) return
  try {
    const raw = sessionStorage.getItem(PERSIST_KEY)
    const bag = raw ? JSON.parse(raw) : {}
    bag[key] = { url, exp: Date.now() + PERSIST_TTL_MS }
    const keys = Object.keys(bag)
    if (keys.length > 400) {
      keys
        .sort((a, b) => (bag[a].exp || 0) - (bag[b].exp || 0))
        .slice(0, keys.length - 300)
        .forEach((k) => delete bag[k])
    }
    sessionStorage.setItem(PERSIST_KEY, JSON.stringify(bag))
  } catch {
    /* quota / private mode */
  }
}

/** URL segura para CSS background-image — bloqueia javascript: e quotes. */
export function safeCssUrl(url) {
  if (!url || typeof url !== 'string') return ''
  const trimmed = url.trim()
  if (!/^https?:\/\//i.test(trimmed) && !trimmed.startsWith('/')) return ''
  if (/["'()\\]/.test(trimmed)) return ''
  return trimmed
}

/**
 * Resolve vários paths em lote (1 request createSignedUrls quando privado).
 * Paths, /object/public/ e /object/sign/ expirados na BD → signed fresca.
 */
export async function resolveImageUrls(paths, placeholder = PLACEHOLDER, options = {}) {
  const input = Array.isArray(paths) ? paths : []
  if (!input.length) return []

  const transform =
    options.transform && transformEnabled() ? options.transform : null

  if (!storagePrivateEnabled()) {
    return input.map((path) => {
      if (!path) return placeholder
      if (typeof path === 'string' && path.trim().startsWith('data:')) return path.trim()
      return getImageUrl(path) || placeholder
    })
  }

  const out = Array.from({ length: input.length }, () => placeholder)
  const needIdx = []
  const needPaths = []

  for (let i = 0; i < input.length; i++) {
    const path = input[i]
    if (!path) continue
    if (typeof path === 'string' && path.trim().startsWith('data:')) {
      out[i] = path.trim()
      continue
    }
    const raw = String(path).trim()

    if (needsPrivateSign(raw)) {
      const key = cacheKey(raw, transform)
      if (!key) continue
      const mem = signedMemo.get(key)
      if (mem) {
        out[i] = mem
        continue
      }
      const persisted = readPersist(key)
      if (persisted) {
        signedMemo.set(key, persisted)
        out[i] = persisted
        continue
      }
      needIdx.push(i)
      needPaths.push(raw)
      continue
    }

    // URL externa (não storage Diomika)
    if (/^https?:\/\//i.test(raw) && !isPlaceholderUrl(raw)) {
      out[i] = raw
    }
  }

  if (needPaths.length) {
    const { getSignedImageUrls } = await import('@/lib/supabase')
    const signed = await getSignedImageUrls(needPaths, 3600, transform)
    for (let j = 0; j < needPaths.length; j++) {
      const url = signed[j]
      const key = cacheKey(needPaths[j], transform)
      if (
        key &&
        url &&
        isReadyUrl(url) &&
        (/\/object\/sign\//i.test(url) || /\/render\/image\/sign\//i.test(url))
      ) {
        signedMemo.set(key, url)
        writePersist(key, url)
        out[needIdx[j]] = url
      } else {
        out[needIdx[j]] = placeholder
      }
    }
  }

  return out
}

export async function resolveImageUrl(path, placeholder = PLACEHOLDER, options = {}) {
  const [url] = await resolveImageUrls([path], placeholder, options)
  return url
}

/** Sync — só paths já signed frescos em memória, ou modo público. */
export function formatImageUrl(path, placeholder = PLACEHOLDER) {
  if (!path) return placeholder
  if (storagePrivateEnabled()) {
    const value = typeof path === 'string' ? path.trim() : ''
    const key = cacheKey(value, null)
    if (key && signedMemo.has(key)) return signedMemo.get(key)
    // Não confiar em signed/public da BD (expiram / 403)
    return placeholder
  }
  const url = getImageUrl(path)
  return url || placeholder
}

export function parseDimensions(dim) {
  const match = String(dim).match(/^(\d+)x(\d+)$/)
  if (!match) return 0
  return parseInt(match[1], 10) * parseInt(match[2], 10)
}
