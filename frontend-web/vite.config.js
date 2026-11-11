import { fileURLToPath, URL } from 'node:url'
import path from 'node:path'
import process from 'node:process'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

/**
 * Para onde `npm run dev` (e o `vite preview`) encaminha `/api`, GET e POST (FE-20). Por omissão a API local
 * (`python deploy/start_local_api.py`, porta DIOMIKA_API_PORT, 8001). Antes era a de produção, e os testes locais
 * liam e tentavam escrever em produção. Outra API (a de produção, só para ler) pede-se de propósito, com
 * DIOMIKA_API_ORIGIN na linha de comandos; nunca vem do `.env` da raiz, que é o de produção.
 */
export function devApiTarget(env = process.env) {
  const origin = String(env.DIOMIKA_API_ORIGIN || '').trim().replace(/\/+$/, '')
  return origin || `http://127.0.0.1:${env.DIOMIKA_API_PORT || 8001}`
}

// https://vitejs.dev/config/
export default defineConfig(({ mode, command }) => {
  const rootEnv = loadEnv(mode, path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..'), '')
  const apiTarget = devApiTarget()
  if (command === 'serve' && !/^http:\/\/(127\.0\.0\.1|localhost)[:/]/.test(apiTarget)) {
    console.warn(`[diomika] /api vai para ${apiTarget}: os formulários que enviar escrevem lá.`)
  }
  let supabaseOrigin = ''
  try {
    if (rootEnv.VITE_SUPABASE_URL) {
      supabaseOrigin = new URL(rootEnv.VITE_SUPABASE_URL).origin
    }
  } catch {
    supabaseOrigin = ''
  }

  return {
    envDir: path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..'),
    plugins: [
      vue(),
      {
        name: 'diomika-preconnect',
        transformIndexHtml: {
          order: 'post',
          handler(html, ctx) {
            // No servidor de desenvolvimento não se liga a produção só por existir (FE-20).
            if (ctx.server) return html
            // Sem `api.diomika.com`: os GET vão para `/api` no próprio domínio e só o envio de formulários o usa (PERF-11).
            const hints = []
            if (supabaseOrigin) {
              hints.unshift(
                `<link rel="preconnect" href="${supabaseOrigin}" crossorigin>`,
                `<link rel="dns-prefetch" href="${supabaseOrigin}">`,
              )
            }
            if (ctx.bundle) {
              for (const fileName of Object.keys(ctx.bundle)) {
                if (/archivo-pt.*\.woff2$/.test(fileName)) {
                  const href = fileName.startsWith('assets/') ? `/${fileName}` : `/assets/${fileName}`
                  hints.push(
                    `<link rel="preload" href="${href}" as="font" type="font/woff2" crossorigin>`,
                  )
                }
              }
            }
            return html.replace('</head>', `    ${hints.join('\n    ')}\n  </head>`)
          },
        },
      },
    ],
    build: {
      sourcemap: false,
      minify: 'esbuild',
      cssCodeSplit: true,
      assetsInlineLimit: 0,
      modulePreload: {
        polyfill: false,
        resolveDependencies(_filename, deps) {
          return deps.filter((d) => !d.includes('supabase') && !d.includes('posthog'))
        },
      },
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return
            if (id.includes(`${path.sep}@supabase${path.sep}`) || id.includes('supabase-js')) {
              return 'supabase'
            }
            if (id.includes('posthog')) return 'posthog'
            if (id.includes('vue-router') || id.includes(`${path.sep}vue${path.sep}`) || id.includes('/vue/')) {
              return 'vue'
            }
          },
        },
      },
    },
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          secure: true,
          rewrite: (p) => p.replace(/^\/api/, ''),
          configure: (proxy) => {
            proxy.on('proxyReq', (proxyReq) => {
              // A origem do Vite (127.0.0.1:5173) não está no CORS de produção.
              proxyReq.removeHeader('origin')
            })
          },
        },
      },
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
  }
})
