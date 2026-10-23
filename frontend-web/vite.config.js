import { fileURLToPath, URL } from 'node:url'
import path from 'node:path'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const rootEnv = loadEnv(mode, path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..'), '')
  // `npm run dev` fala com a API em produção por omissão (como o backoffice):
  // antes apontava sempre para 127.0.0.1:8001 e, sem API local a correr, todos
  // os pedidos davam «Failed to fetch». DIOMIKA_LOCAL_API=1 → API local.
  const useLocalApi = (process.env.DIOMIKA_LOCAL_API || rootEnv.DIOMIKA_LOCAL_API) === '1'
  const apiOrigin = (rootEnv.DIOMIKA_API_ORIGIN || 'https://api.diomika.com').replace(/\/+$/, '')
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
            const hints = [
              '<link rel="preconnect" href="https://api.diomika.com" crossorigin>',
              '<link rel="dns-prefetch" href="https://api.diomika.com">',
            ]
            if (supabaseOrigin) {
              hints.unshift(
                `<link rel="preconnect" href="${supabaseOrigin}" crossorigin>`,
                `<link rel="dns-prefetch" href="${supabaseOrigin}">`,
              )
            }
            if (ctx.bundle) {
              for (const fileName of Object.keys(ctx.bundle)) {
                if (/archivo-latin-wdth-normal.*\.woff2$/.test(fileName)) {
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
          target: useLocalApi ? 'http://127.0.0.1:8001' : apiOrigin,
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
