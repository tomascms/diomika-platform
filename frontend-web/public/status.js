// Página de estado (public/status.html). Ficheiro à parte porque a CSP da loja (script-src 'self') bloqueia o <script>
// dentro do HTML: com ele lá dentro a página nunca chegava a verificar nada.
const TARGETS = [
  { id: 'api', name: 'API Diomika', url: 'https://api.diomika.com/health', ok: (r, t) => r.ok && /online|ready/.test(t) },
  { id: 'api-ready', name: 'API + base de dados', url: 'https://api.diomika.com/health/ready', ok: (r) => r.ok },
  { id: 'site', name: 'Loja online', url: 'https://www.diomika.com/', ok: (r) => r.ok },
]

function div(className, text) {
  const el = document.createElement('div')
  el.className = className
  if (text) el.textContent = text
  return el
}

function setPill(el, state, label) {
  el.className = `pill ${state}`
  el.textContent = label
}

function card(target) {
  const el = div('card')
  el.id = `card-${target.id}`
  const text = document.createElement('div')
  text.append(div('name', target.name), div('detail', 'A verificar…'))
  const pill = document.createElement('span')
  setPill(pill, 'wait', '…')
  el.append(text, pill)
  return el
}

async function probe(target) {
  const t0 = performance.now()
  try {
    const r = await fetch(target.url, { cache: 'no-store', mode: 'cors' })
    const text = await r.text()
    const ms = Math.round(performance.now() - t0)
    const good = target.ok(r, text)
    return { good, ms, detail: good ? `${ms} ms` : `HTTP ${r.status}` }
  } catch {
    return { good: false, ms: null, detail: 'Indisponível' }
  }
}

async function render() {
  document.getElementById('checks').replaceChildren(...TARGETS.map(card))

  for (const target of TARGETS) {
    const result = await probe(target)
    const el = document.getElementById(`card-${target.id}`)
    el.querySelector('.detail').textContent = result.detail
    setPill(el.querySelector('.pill'), result.good ? 'ok' : 'bad', result.good ? 'Operacional' : 'Problema')
  }
}

render()
setInterval(render, 60000)
