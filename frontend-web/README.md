# Loja (Vue 3 + Cloudflare Pages)

Vue 3, Vue Router, Vite. Sem framework de UI: CSS próprio com tokens em `src/assets/main.css`.

## Peças
| Onde | O quê |
|---|---|
| `src/views/` | Início, catálogo, categoria (filtros, pesquisa local), produto (cores, quantidades por regra), pedido de orçamento, contacto, pesquisa, páginas legais |
| `src/components/SoftImage.vue` | Imagem com esqueleto, miniaturas 480/960 px por `srcset` e recuo para o original |
| `src/composables/` | Carrinho (sem dados pessoais no browser), catálogo com cache de sessão, Turnstile, meta/SEO |
| `functions/_middleware.js` | CSP e cabeçalhos de segurança, domínio canónico, bloqueio de caminhos sensíveis |
| `functions/api/[[path]].js` | Proxy de leitura do catálogo com cache no edge por versão, timeouts e *stale-if-error* |
| `scripts/prerender-seo.mjs` | Gera no build as páginas de categoria/produto com título, descrição, canonical, JSON-LD e *preload* da imagem principal; sitemap |

## Comandos
```bash
npm ci
npm run dev          # desenvolvimento
npm run build:prod   # build de produção (+ _headers de produção); ver docs/runbook.md §1
npx eslint src       # lint (o CI corre também oxlint)
```
`deploy/verify_csp.py` e `deploy/verify_bundle_secrets.py` correm no CI depois do build.
