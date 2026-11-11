import { test } from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { COMPANY, COMPLAINTS_BOOK_URL, callCostNote } from '../src/lib/constants.js'

// As páginas HTML que a loja serve tal como estão em public/ (sem passar pela SPA): a 404, a de estado e a de
// manutenção. Só lê ficheiros do repositório.
const PUBLIC = new URL('../public/', import.meta.url)
const read = (name) => readFileSync(new URL(name, PUBLIC), 'utf8')
// Sem comentários: os de cada ficheiro explicam o que a CSP bloqueia e citam as próprias etiquetas.
const markup = (name) => read(name).replace(/<!--[\s\S]*?-->/g, '')
const text = (name) =>
  markup(name)
    .replace(/<(style|script)[\s\S]*?<\/\1>/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')

const PAGES = ['404.html', 'status.html', 'maintenance.html']
// Servidas pela loja, com a CSP (style-src e script-src 'self'). A de manutenção vai sozinha para o artefacto de
// manutenção, sem CSP: deploy/launch_lib.py copia só o HTML, por isso o CSS dela fica lá dentro.
const UNDER_CSP = ['404.html', 'status.html']

test('as três páginas têm o rodapé curto (DL 7/2004, art. 10.º), com os dados de COMPANY: o registo e a RAL ficam em «Informação legal»', () => {
  for (const page of PAGES) {
    const body = text(page)
    for (const part of [
      COMPANY.legalName,
      COMPANY.address,
      COMPANY.postal,
      `NIPC ${COMPANY.nif}`,
      COMPANY.phoneDisplay,
      callCostNote(COMPANY.phoneDisplay),
    ]) {
      assert.ok(body.includes(part), `${page} sem «${part}»`)
    }
    for (const link of ['Condições de venda', 'Perguntas frequentes', 'Privacidade', 'Cookies', 'Informação legal', 'Livro de Reclamações', 'Todos os direitos reservados']) {
      assert.ok(body.includes(link), `${page} sem «${link}»`)
    }
    assert.ok(markup(page).includes(COMPLAINTS_BOOK_URL), `${page} sem a ligação ao Livro de Reclamações`)
    assert.doesNotMatch(body, /Matrícula|Sociedade unipessoal|TRIAVE/, `${page} com texto que só a «Informação legal» leva`)
  }
})

test('as páginas servidas pela loja não têm CSS nem JavaScript dentro do HTML (a CSP bloqueia-os, BR-01)', () => {
  for (const page of UNDER_CSP) {
    const html = markup(page)
    assert.doesNotMatch(html, /<style[\s>]/i, `${page} tem <style>`)
    assert.doesNotMatch(html, /\sstyle\s*=/i, `${page} tem style=""`)
    assert.doesNotMatch(html, /<script(?![^>]*\ssrc=)[^>]*>/i, `${page} tem <script> inline`)
    assert.doesNotMatch(html, /\son[a-z]+\s*=/i, `${page} tem um manipulador de evento inline`)
    // O que carregam existe em public/ (e por isso vai no build).
    const files = [...html.matchAll(/(?:href|src)="\/([^"/?#]+\.(?:css|js))"/g)].map((match) => match[1])
    assert.ok(files.length > 0, `${page} não liga a nenhum ficheiro`)
    for (const file of files) assert.ok(existsSync(new URL(file, PUBLIC)), `${page} liga a /${file}, que não existe`)
  }
  assert.match(markup('404.html'), /href="\/404\.css"/)
  assert.match(markup('status.html'), /href="\/status\.css"/)
  assert.match(markup('status.html'), /src="\/status\.js"/)
})

test('a página de manutenção é de um só ficheiro (vai sozinha para o artefacto)', () => {
  const html = markup('maintenance.html')
  assert.match(html, /<style>/)
  assert.doesNotMatch(html, /<link[^>]+stylesheet/i)
  assert.doesNotMatch(html, /<script/i)
})

test('a 404 tem o que A11Y-12 e FE-04 pedem: <main>, título, cabeçalho com a navegação e saídas (catálogo, contacto, WhatsApp)', () => {
  const html = markup('404.html')

  assert.match(html, /<html lang="pt-PT">/)
  assert.match(html, /<main[\s>]/)
  assert.match(html, /<h1>Página não encontrada<\/h1>/)
  assert.match(html, /<header[\s>][\s\S]*<nav[^>]+aria-label="Principal"[\s\S]*<\/header>/)
  for (const href of ['/', '/categorias', '/contacto', '/pesquisa', '/sobre', '/carrinho']) {
    assert.ok(html.includes(`href="${href}"`), `404 sem ligação para ${href}`)
  }
  assert.ok(html.includes(`href="https://wa.me/${COMPANY.whatsappE164}?text=`), '404 sem WhatsApp')
  assert.match(html, /<footer[\s>][\s\S]*<address/)
  // Quem salta para o conteúdo cai no <main>.
  assert.match(html, /<a class="skip-link" href="#main">/)
  assert.match(html, /<main id="main">/)
})

test('a página de estado verifica os serviços sem innerHTML (o texto vem de constantes, mas não precisa dele)', () => {
  const script = read('status.js')
  assert.doesNotMatch(script, /innerHTML|outerHTML/)
  assert.match(script, /api\.diomika\.com\/health/)
})
