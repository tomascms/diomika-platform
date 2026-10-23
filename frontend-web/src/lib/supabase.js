import {
  supabaseConfigured,
  supabaseUrl,
  supabaseAnonKey,
  storageBucket,
  normalizeStorageUrl,
  storageObjectPath,
  getImageUrl,
} from '@/lib/supabaseConfig'

export {
  supabaseConfigured,
  storageBucket,
  normalizeStorageUrl,
  storageObjectPath,
  getImageUrl,
} from '@/lib/supabaseConfig'

/** Cliente lazy — só carrega @supabase/supabase-js on-demand. */
let _client = null
let _loading = null

export async function ensureSupabase() {
  if (_client) return _client
  if (!supabaseConfigured) return null
  if (!_loading) {
    _loading = import('@supabase/supabase-js')
      .then(({ createClient }) => {
        _client = createClient(supabaseUrl, supabaseAnonKey)
        return _client
      })
      .catch((err) => {
        _loading = null
        throw err
      })
  }
  return _loading
}

export function getSupabaseSync() {
  return _client
}

const DEFAULT_EXPIRES = 3600

export async function getSignedImageUrl(path, expiresIn = DEFAULT_EXPIRES, transform = null) {
  const [url] = await getSignedImageUrls([path], expiresIn, transform)
  return url
}

async function mapPool(items, concurrency, fn) {
  const out = Array.from({ length: items.length })
  let next = 0
  async function worker() {
    while (next < items.length) {
      const i = next++
      out[i] = await fn(items[i], i)
    }
  }
  const n = Math.min(concurrency, Math.max(1, items.length))
  await Promise.all(Array.from({ length: n }, () => worker()))
  return out
}

export async function getSignedImageUrls(paths, expiresIn = DEFAULT_EXPIRES, transform = null) {
  const list = Array.isArray(paths) ? paths : []
  if (!list.length || !supabaseConfigured) return list.map(() => '')

  const client = await ensureSupabase()
  if (!client) return list.map(() => '')

  const out = Array.from({ length: list.length }, () => '')
  const storagePaths = []
  const storageIdx = []

  for (let i = 0; i < list.length; i++) {
    const path = list[i]
    if (!path) continue
    if (typeof path === 'string' && /^data:/i.test(path.trim())) {
      out[i] = path.trim()
      continue
    }
    const storagePath = storageObjectPath(path)
    if (!storagePath) {
      const raw = String(Array.isArray(path) ? path[0] : path).trim()
      out[i] = /^https?:\/\//i.test(raw) ? normalizeStorageUrl(raw) : ''
      continue
    }
    storagePaths.push(storagePath)
    storageIdx.push(i)
  }

  if (!storagePaths.length) return out

  const unique = [...new Set(storagePaths)]
  // Sempre preferir batch createSignedUrls (1 request). Transforms por imagem
  // são lentos e falham em muitos planos — só com VITE_IMAGE_TRANSFORM=1.
  const hasTransform =
    transform && typeof transform === 'object' && Object.keys(transform).length > 0

  if (hasTransform) {
    try {
      const signedByPath = new Map()
      let transformOk = 0
      await mapPool(unique, 8, async (storagePath) => {
        const { data, error } = await client.storage
          .from(storageBucket)
          .createSignedUrl(storagePath, expiresIn, { transform })
        if (!error && data?.signedUrl) {
          signedByPath.set(storagePath, data.signedUrl)
          transformOk += 1
        }
      })
      if (transformOk >= Math.ceil(unique.length * 0.6)) {
        for (let j = 0; j < storagePaths.length; j++) {
          out[storageIdx[j]] = signedByPath.get(storagePaths[j]) || ''
        }
        if (out.every((u, i) => !storageIdx.includes(i) || u)) return out
      }
    } catch {
      /* Image Transformation off → fallback */
    }
  }

  const { data, error } = await client.storage
    .from(storageBucket)
    .createSignedUrls(unique, expiresIn)

  if (error || !Array.isArray(data)) return out

  const byPath = new Map()
  for (const row of data) {
    const signed = row?.signedUrl || row?.signedURL || ''
    if (row?.path && signed) byPath.set(row.path, signed)
  }

  for (let j = 0; j < storagePaths.length; j++) {
    const p = storagePaths[j]
    out[storageIdx[j]] = byPath.get(p) || ''
  }

  // Fallback por índice se a API não devolver path alinhado
  if (Array.isArray(data) && data.length === unique.length) {
    const uniqueSigned = data.map((row) => row?.signedUrl || row?.signedURL || '')
    const uniqueMap = new Map(unique.map((p, i) => [p, uniqueSigned[i]]))
    for (let j = 0; j < storagePaths.length; j++) {
      if (!out[storageIdx[j]]) {
        out[storageIdx[j]] = uniqueMap.get(storagePaths[j]) || ''
      }
    }
  }
  return out
}
