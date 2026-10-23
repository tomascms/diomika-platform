const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''
export const storageBucket = import.meta.env.VITE_SUPABASE_STORAGE_BUCKET || 'product-images'

export const supabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey)
export { supabaseUrl, supabaseAnonKey }

const storagePrivate = /^(1|true|yes)$/i.test(String(import.meta.env.VITE_STORAGE_PRIVATE || '').trim())

export function normalizeStorageUrl(url) {
  if (!url || !/^https?:\/\//i.test(url)) return url

  let cleaned = url.replace('/object/public/public/', '/object/public/')
  // Bucket público: URLs assinadas gravadas na BD (tokens expirados) → URL pública.
  if (!storagePrivate && cleaned.includes('/storage/v1/object/sign/')) {
    cleaned = cleaned.replace('/storage/v1/object/sign/', '/storage/v1/object/public/').split('?')[0]
  }
  const marker = '/storage/v1/object/public/'
  const idx = cleaned.indexOf(marker)
  if (idx === -1) return cleaned

  const prefix = cleaned.slice(0, idx + marker.length)
  let path = cleaned.slice(idx + marker.length).replace(/^\/+/, '')
  if (!path || path.startsWith(`${storageBucket}/`)) return cleaned

  return `${prefix}${storageBucket}/${path}`
}

/** Extrai path interno a partir de URL pública/assinada do Storage. */
export function storageObjectPath(path) {
  if (!path) return ''
  if (Array.isArray(path)) return storageObjectPath(path[0])
  if (typeof path === 'object') {
    if (path?.url) return storageObjectPath(path.url)
    return ''
  }
  let value = String(path).trim()
  if (!value) return ''
  if (/^data:/i.test(value)) return ''

  const markers = [
    `/storage/v1/object/public/${storageBucket}/`,
    `/storage/v1/object/sign/${storageBucket}/`,
    `/storage/v1/object/authenticated/${storageBucket}/`,
    `/storage/v1/render/image/public/${storageBucket}/`,
    `/storage/v1/render/image/sign/${storageBucket}/`,
  ]
  for (const marker of markers) {
    const idx = value.indexOf(marker)
    if (idx !== -1) {
      let rest = value.slice(idx + marker.length)
      rest = rest.split('?')[0]
      return decodeURIComponent(rest.replace(/^\/+/, ''))
    }
  }

  if (/^https?:\/\//i.test(value)) return ''

  if (/^[[{]/.test(value)) {
    try {
      const parsed = JSON.parse(value)
      if (Array.isArray(parsed)) return storageObjectPath(parsed[0])
      if (typeof parsed === 'string') return storageObjectPath(parsed)
    } catch {
      // continua
    }
  }

  let storagePath = value.replace(/\\/g, '/').replace(/^\/+/, '')
  if (storagePath.startsWith(`${storageBucket}/`)) {
    storagePath = storagePath.slice(storageBucket.length + 1)
  }
  return storagePath
}

/** URL pública sem precisar do SDK. */
export function getImageUrl(path) {
  if (!path) return ''

  if (Array.isArray(path)) {
    return getImageUrl(path[0])
  }

  if (typeof path === 'object') {
    if (path?.url) return getImageUrl(path.url)
    return ''
  }

  let value = String(path).trim()
  if (!value) return ''

  if (/^https?:\/\//i.test(value) || /^data:/i.test(value)) {
    return normalizeStorageUrl(value)
  }

  if (!supabaseConfigured || !supabaseUrl) return ''

  const storagePath = storageObjectPath(value)
  if (!storagePath) return ''

  return `${supabaseUrl.replace(/\/$/, '')}/storage/v1/object/public/${storageBucket}/${storagePath}`
}
