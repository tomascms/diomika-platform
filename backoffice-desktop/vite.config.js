import { fileURLToPath, URL } from 'node:url'
import path from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

const backofficeRoot = fileURLToPath(new URL('.', import.meta.url))
const projectRoot = path.resolve(backofficeRoot, '..')

export default defineConfig(({ mode }) => {
  // Só precisamos da API key de dev do monorepo; NÃO injectar VITE_API_BASE_URL da loja.
  const env = loadEnv(mode, projectRoot, '')
  const apiKey = env.API_SECRET_KEY || ''
  const useLocalApi = env.DIOMIKA_LOCAL_API === '1'
  const cloudOrigin = (env.DIOMIKA_API_ORIGIN || 'https://api.diomika.com').replace(/\/+$/, '')
  const desktopGate = (env.DIOMIKA_DESKTOP_GATE || '').trim()

  return {
    envDir: backofficeRoot,
    base: './',
    plugins: [vue()],
    define: {
      __DIOMIKA_DEV_API_KEY__: JSON.stringify(mode === 'development' ? apiKey : ''),
    },
    server: {
      host: '127.0.0.1',
      port: 5174,
      strictPort: true,
      proxy: {
        '/api': {
          target: useLocalApi ? 'http://127.0.0.1:8001' : cloudOrigin,
          changeOrigin: true,
          secure: true,
          rewrite: (p) => p.replace(/^\/api/, ''),
          configure: (proxy) => {
            proxy.on('proxyReq', (proxyReq) => {
              proxyReq.setHeader('User-Agent', 'DiomikaBackoffice/1.0')
              if (desktopGate) proxyReq.setHeader('x-diomika-desktop', desktopGate)
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
