import { test } from 'node:test'
import assert from 'node:assert/strict'
import { COMPANY } from '../src/lib/constants.js'
import { renderViews } from './render-views.mjs'
import { STATIC_PAGES } from './static-pages.mjs'

// Corre o renderizador a sério (o Vite carrega as vistas, o Vue renderiza-as), como o pré-render. Uma vista que passe a
// usar `window` ao arrancar rebenta aqui, no CI, e não no deploy.
const PATHS = STATIC_PAGES.filter((page) => page.noscript).map((page) => page.path)
const text = (html) =>
  html
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&nbsp;| /g, ' ')
    .replace(/\s+/g, ' ')

test('as páginas institucionais marcadas como noscript são as de SEO-10', () => {
  assert.deepEqual(PATHS.toSorted(), [
    '/condicoes-de-venda',
    '/contacto',
    '/cookies',
    '/perguntas-frequentes',
    '/pesquisa',
    '/privacidade',
    '/sobre',
    '/termos',
  ])
})

test('cada uma sai com um <h1> e o seu texto, sem comentários do Vue nem atributos de estilo', async () => {
  const html = await renderViews(PATHS)

  assert.deepEqual(Object.keys(html).toSorted(), PATHS.toSorted())
  const expected = {
    '/sobre': 'Têxteis para o lar, de Caldas das Taipas',
    '/contacto': 'Contacto',
    '/pesquisa': 'Pesquisar catálogo',
    '/privacidade': COMPANY.legalName,
    '/termos': 'Livro de Reclamações',
    '/cookies': 'Cloudflare Turnstile',
    '/condicoes-de-venda': 'Condições gerais de venda',
    '/perguntas-frequentes': 'Perguntas frequentes',
  }
  for (const path of PATHS) {
    assert.equal((html[path].match(/<h1[\s>]/g) ?? []).length, 1, `${path}: um <h1>`)
    assert.ok(text(html[path]).includes(expected[path]), `${path} sem «${expected[path]}»`)
    // A pesquisa e o contacto são sobretudo um formulário: ~200 caracteres; os textos legais têm milhares.
    assert.ok(text(html[path]).length > 150, `${path}: texto mais pequeno do que devia`)
    assert.doesNotMatch(html[path], /<!--|data-v-/, `${path}: restos do Vue`)
    assert.doesNotMatch(html[path], /<script|<style/i, `${path}`)
  }
})

test('as ligações do texto são endereços verdadeiros da loja, não ligações vazias', async () => {
  const { '/sobre': about } = await renderViews(['/sobre'])

  const hrefs = [...about.matchAll(/href="([^"]*)"/g)].map((match) => match[1])
  assert.ok(hrefs.length > 0)
  assert.ok(hrefs.every((href) => href.startsWith('/') || href.startsWith('http') || href.startsWith('tel:') || href.startsWith('#')), hrefs.join(' '))
  assert.ok(hrefs.includes('/contacto') || hrefs.includes('/categorias'))
})

test('um endereço sem vista rebenta em vez de dar um <noscript> vazio', async () => {
  await assert.rejects(renderViews(['/nao-existe']), /não há vista/)
})
