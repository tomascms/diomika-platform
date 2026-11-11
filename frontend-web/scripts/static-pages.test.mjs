import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { STATIC_PAGES } from './static-pages.mjs'

// Só lê a lista e os ficheiros do repositório: nunca corre o pré-render, que pede o catálogo à API.
const read = (relative) => readFileSync(new URL(relative, import.meta.url), 'utf8')
const bySitemap = STATIC_PAGES.filter((page) => page.sitemap !== false)
const NEW_LEGAL_PAGES = ['/condicoes-de-venda', '/perguntas-frequentes']

test('condições gerais de venda e perguntas frequentes são pré-renderizadas, com título e descrição', () => {
  for (const path of NEW_LEGAL_PAGES) {
    const page = STATIC_PAGES.find((candidate) => candidate.path === path)
    assert.ok(page, `${path} falta em STATIC_PAGES`)
    assert.ok(page.title && page.description, `${path} sem título ou descrição próprios`)
  }
})

test('as duas páginas novas entram no sitemap gerado e no public/sitemap.xml', () => {
  const published = read('../public/sitemap.xml')
  for (const path of NEW_LEGAL_PAGES) {
    assert.ok(
      bySitemap.some((page) => page.path === path),
      `${path} fora do sitemap gerado`,
    )
    assert.ok(
      published.includes(`<loc>https://www.diomika.com${path}</loc>`),
      `${path} fora de public/sitemap.xml`,
    )
  }
})

test('todas as páginas do sitemap gerado estão também em public/sitemap.xml', () => {
  const published = read('../public/sitemap.xml')
  for (const { path } of bySitemap) {
    const loc = path === '/' ? 'https://www.diomika.com/' : `https://www.diomika.com${path}`
    assert.ok(published.includes(`<loc>${loc}</loc>`), `${path} fora de public/sitemap.xml`)
  }
})

test('cada página estática tem rota no router (um erro de escrita dava uma página gerada para um 404)', () => {
  const routes = new Set(
    [...read('../src/router/routes.js').matchAll(/path: '([^']+)'/g)].map((m) => m[1]),
  )
  for (const { path } of STATIC_PAGES) assert.ok(routes.has(path), `${path} não tem rota`)
})

test('caminhos únicos, e todas as páginas, menos o início, com título e descrição', () => {
  const paths = STATIC_PAGES.map((page) => page.path)
  assert.equal(new Set(paths).size, paths.length)
  for (const page of STATIC_PAGES.filter((candidate) => candidate.path !== '/')) {
    assert.ok(page.title && page.description, `${page.path} sem título ou descrição`)
  }
})
