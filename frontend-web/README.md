# Loja (Vue 3 + Cloudflare Pages)

Vue 3, Vue Router, Vite. Sem framework de UI: CSS próprio com tokens em `src/assets/main.css`.

## Peças
| Onde | O quê |
|---|---|
| `src/views/` | Início, catálogo, categoria (filtros, pesquisa local), produto (cores, quantidades por regra), pedido de orçamento, contacto, pesquisa, páginas legais |
| `src/components/SoftImage.vue` | Imagem com esqueleto, miniaturas 480/960 px por `srcset` e recuo para o original |
| `src/composables/` | Carrinho (sem dados pessoais no browser), catálogo com cache de sessão, Turnstile, meta/SEO |
| `src/lib/` | Lógica pura, testada com `node --test`: textos do catálogo (`describe.js`, usado também pelo pré-render), quantidades (`quantity.js`), linha do pedido (`cartItem.js`), pedido rápido por EAN (`quickOrder.js`), NIF, armazenamento |
| `src/views/QuickOrderView.vue`, `CataloguePrintView.vue` | Pedido rápido por EAN (`/pedido-rapido`) e catálogo para imprimir ou guardar em PDF (`/catalogo-imprimir`, CSS de impressão: sem biblioteca de PDF) |
| `functions/_middleware.js` | CSP e cabeçalhos de segurança, domínio canónico, bloqueio de caminhos sensíveis |
| `functions/api/[[path]].js` | Proxy de leitura do catálogo com cache no edge por versão, timeouts e *stale-if-error* |
| `scripts/prerender-seo.mjs` | Gera no build as páginas de categoria/produto com título, descrição, canonical, JSON-LD e *preload* da imagem principal; sitemap. As páginas estáticas (título, descrição, sitemap) estão em `scripts/static-pages.mjs` |

## Comandos
```bash
npm ci
npm run dev          # desenvolvimento: /api vai para a API LOCAL (ver abaixo), nunca para a de produção
npm run build:prod   # build de produção (+ _headers de produção); ver docs/runbook.md §1
npm run lint         # oxlint + eslint, só verificam; `npm run lint:fix` corrige
npm run format       # prettier --write src/; `npm run format:check` só verifica
npm test             # node --test: lógica pura (src/lib), pré-render e a configuração do Vite
npm run test:e2e:local   # Playwright contra a loja construída e a API simulada (e2e/local)
```

### Desenvolver sem tocar na produção
`npm run dev` encaminha `/api` (GET e POST) para a API local em `127.0.0.1:8001`: arranque-a com
`python deploy/start_local_api.py` (a porta muda com `DIOMIKA_API_PORT`). Antes ia para `api.diomika.com`, e os testes
locais liam e tentavam escrever em produção. Outra API só se pede de propósito (`DIOMIKA_API_ORIGIN=<url> npm run dev`,
e o servidor avisa se não for local); nunca vem do `.env` da raiz, que é o de produção.

Duas coisas que isto não muda: a API local arranca com o `.env` da raiz, ou seja, com as credenciais de produção (para
não tocar na produção, ponha no ambiente as de uma base de teste antes de a arrancar); e o Vite lê as `VITE_*` desse
mesmo `.env`. Para valores de teste na loja, copie o bloco «Loja (frontend-web)» do `.env.example` da raiz para um
`.env.development.local` (o Vite dá-lhe prioridade e o git ignora-o).
`deploy/verify_csp.py` e `deploy/verify_bundle_secrets.py` correm no CI depois do build.
