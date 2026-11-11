// Vigia da API e da loja. De 10 em 10 minutos:
// - chama /health/live da API: o Render adormece o serviço grátis ao fim de 15 minutos sem pedidos, e acordar demora
//   cerca de 1 minuto; com esta chamada nunca adormece (24 h × 31 dias = 744 h, dentro das 750 h grátis por mês);
// - abre www.diomika.com (DNS, Pages e certificado; em 2026-11-10 a loja caiu por faltar o CNAME e ninguém foi avisado);
// - uma vez por hora, abre a ficha de cada modelo da loja pelo URL que a loja faz (o do QR da etiqueta); em 2026-11-10
//   os cintos davam «já não está disponível» porque o URL vinha do nome e a API só procurava o slug gravado;
// - se alguma não responde (duas tentativas), avisa por ntfy, no máximo uma vez por hora.
// Segredo: ALERT_WEBHOOK_URL.

const CHECKS = [
  ['A API não responde.', 'https://api.diomika.com/health/live'],
  ['A loja (www.diomika.com) não abre.', 'https://www.diomika.com/'],
]

export default {
  async scheduled(event, env) {
    const down = []
    for (const [text, url] of CHECKS) {
      if (!((await alive(url)) || (await alive(url)))) down.push(text)
    }
    const hourly = new Date(event.scheduledTime).getUTCMinutes() < 10
    if (hourly && !down.length) down.push(...(await brokenModels()))
    if (down.length && hourly) {
      await notify(env, down.join(' '))
    }
  },
}

const API = 'https://api.diomika.com'
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

// Igual a slugifyName/categorySlug/modelSlug da loja (frontend-web/src/lib/catalogRoutes.js).
export function slugify(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}
const categorySlug = (c) => (c.slug && !UUID.test(c.slug) ? c.slug.trim() : slugify(c.nome))

async function getJson(path) {
  const r = await fetch(API + path, {
    headers: { 'user-agent': 'DiomikaHealthcheck/1.0' },
    signal: AbortSignal.timeout(60000),
  })
  if (!r.ok) throw new Error(`${r.status} ${path}`)
  return r.json()
}

/** Ficha de cada modelo visível de cada categoria com modelos, pelo URL da loja. Devolve o texto dos que falham. */
export async function brokenModels() {
  const broken = []
  try {
    for (const cat of await getJson('/categorias')) {
      if (!cat.modelos_visiveis) continue
      const tipo = encodeURIComponent(cat.tipo_catalogo)
      const models = await getJson(`/catalogo/${tipo}/modelos-catalogo/${cat.id}`)
      for (const m of models.filter((x) => x.visibilidade !== false)) {
        const path = `/catalogo/${tipo}/modelo-detalhe/slug/${encodeURIComponent(categorySlug(cat))}/${encodeURIComponent(slugify(m.nome))}`
        try {
          await getJson(path)
        } catch {
          broken.push(`Não abre: ${cat.nome.trim()} / ${m.nome}.`)
        }
      }
    }
  } catch (e) {
    broken.push(`Catálogo não lido (${e.message}).`)
  }
  return broken
}

async function alive(url) {
  try {
    const r = await fetch(url, {
      headers: { 'user-agent': 'DiomikaHealthcheck/1.0' },
      // Folga para o arranque a frio do Render (até ~1 minuto) depois de um deploy.
      signal: AbortSignal.timeout(60000),
    })
    return r.ok
  } catch {
    return false
  }
}

function notify(env, text) {
  return fetch(env.ALERT_WEBHOOK_URL, {
    method: 'POST',
    headers: { Title: 'Diomika: vigia', Priority: 'high' },
    body: text,
  })
}
