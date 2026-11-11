// @ts-check
import process from 'node:process'
import { defineConfig } from '@playwright/test'

// Projecto `local`: a loja construída (`vite build`) e servida por `vite preview`, com a API
// simulada por e2e/local/helpers.js (mockApi). Nada sai de localhost.
// Projecto `prod`: e2e/critical.spec.js contra os URLs que a pessoa indicar (exige E2E_API_URL).
const PORT = 4273
const ORIGIN = `http://127.0.0.1:${PORT}`
// Fora de `dist` (o que se publica) e já ignorado pelo git e pelos linters.
const OUT_DIR = 'node_modules/.cache/e2e-dist'

// O `.env` da raiz é de produção e o Vite lê-o; as variáveis do processo têm prioridade.
// Por isso a loja do e2e leva todas as VITE_* que o código lê, com valores de teste.
const STORE_ENV = {
  VITE_API_BASE_URL: `${ORIGIN}/api`,
  VITE_EDGE_API: '1',
  // Sem Supabase: nada de recurso directo à base de dados a partir do browser.
  VITE_SUPABASE_URL: '',
  VITE_SUPABASE_ANON_KEY: '',
  VITE_SUPABASE_STORAGE_BUCKET: 'product-images',
  VITE_STORAGE_PRIVATE: '0',
  VITE_IMAGE_TRANSFORM: '0',
  // Chave falsa: sem ela o banner de cookies nunca aparece e os testes de consentimento
  // passariam em vazio. Qualquer pedido ao PostHog é abortado e reprova o teste (mockApi).
  VITE_POSTHOG_KEY: 'phc_e2e_chave_falsa',
  VITE_POSTHOG_HOST: 'https://eu.i.posthog.com',
  VITE_TURNSTILE_SITE_KEY: '1x00000000000000000000AA',
  VITE_BETA_MODE: '0',
  // Proxy `/api` do `vite preview` (herdado de vite.config.js): porta fechada, nunca chega à
  // produção nem a uma API local ligada à produção.
  DIOMIKA_API_ORIGIN: 'http://127.0.0.1:9',
}

// `--project=prod` não precisa da loja local: nesse caso não a constrói.
const selected = process.argv.flatMap((arg, i, argv) => {
  if (arg.startsWith('--project=')) return arg.slice('--project='.length)
  return arg === '--project' ? argv[i + 1] : []
})
const needsStore = selected.length === 0 || selected.includes('local')

export default defineConfig({
  timeout: 60_000,
  retries: 1,
  // Um worker por vez. Medido neste PC Windows (2026-10-29): com 3 ou mais browsers a navegar ao
  // mesmo tempo, os pedidos a 127.0.0.1 ficam parados em degraus de ~10 s e o teste esgota o tempo
  // (60 testes: 2 workers sem falhas em 4 execuções, 3 workers 1 falha, 4 workers 10 falhas).
  // Reproduz-se sem Playwright Test e com um servidor estático qualquer, por isso não é da loja
  // nem do harness. Em série não falha. Noutra máquina sobe-se na linha de comandos: --workers=4.
  workers: 1,
  use: {
    headless: true,
    userAgent: 'Mozilla/5.0 (compatible; DiomikaE2E/1.0)',
  },
  reporter: 'list',
  projects: [
    {
      name: 'local',
      testDir: './e2e/local',
      // Hermético: uma repetição só esconderia um teste instável.
      retries: 0,
      use: {
        baseURL: ORIGIN,
        // Rede de segurança além de mockApi: fora de localhost nem o DNS resolve
        // (preconnect do index.html, beacons ao fechar a página).
        launchOptions: {
          args: ['--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1'],
        },
      },
    },
    { name: 'prod', testDir: './e2e', testMatch: /critical\.spec\.js$/ },
  ],
  // Constrói sempre de novo (2 s) e não reutiliza servidores: nunca testa uma build antiga.
  webServer: needsStore
    ? {
        command: `npx vite build --outDir ${OUT_DIR} && npx vite preview --outDir ${OUT_DIR} --port ${PORT} --strictPort`,
        url: ORIGIN,
        env: STORE_ENV,
        timeout: 120_000,
      }
    : undefined,
})
