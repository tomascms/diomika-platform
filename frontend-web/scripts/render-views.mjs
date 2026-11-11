/**
 * O texto das páginas da loja que não vêm da API (Sobre nós, Contacto, Privacidade, Termos, Cookies, Condições de
 * venda, Perguntas frequentes e Pesquisa), escrito em HTML para o `<noscript>` de cada página pré-renderizada
 * (auditoria SEO-10). Antes o `<noscript>` ficava vazio e o HTML não tinha nenhum `<h1>`: pré-visualizações, assistentes
 * de IA e motores de busca sem JavaScript viam só o título e a descrição.
 *
 * Renderiza as próprias vistas (`src/views/*.vue`) com o renderizador de servidor do Vue, carregadas pelo Vite: o texto
 * que o Google lê sem JavaScript é o que a loja mostra com ele, sem uma segunda cópia para manter (e estas páginas têm
 * texto legal). Sem dependências novas: `vue/server-renderer` vem com o Vue.
 */
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createMemoryHistory, createRouter } from 'vue-router'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

/** Sem os comentários que o Vue deixa para a hidratação e sem os atributos dos estilos «scoped»: só o texto e a estrutura. */
const tidy = (html) =>
  html
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\sdata-v-[0-9a-f]{8}(?:="")?/g, '')
    .trim()

/**
 * @param {string[]} paths endereços da loja (`/sobre`, …)
 * @returns {Promise<Record<string, string>>} o HTML de cada vista, por endereço
 */
export async function renderViews(paths) {
  const vite = await createServer({
    root: ROOT,
    configFile: path.join(ROOT, 'vite.config.js'),
    appType: 'custom',
    logLevel: 'error',
    // Só carrega módulos: não abre porta, não vigia ficheiros e não analisa dependências.
    server: { middlewareMode: true, hmr: false, ws: false, watch: null },
    optimizeDeps: { noDiscovery: true, include: [] },
  })
  try {
    const { routes } = await vite.ssrLoadModule('/src/router/routes.js')
    const html = {}
    for (const url of paths) {
      // As mesmas rotas da loja: as vistas ligam-se por nome (`{ name: 'home' }`).
      const router = createRouter({ history: createMemoryHistory(), routes })
      await router.push(url)
      await router.isReady()
      const view = router.currentRoute.value.matched[0]?.components?.default
      if (!view || router.currentRoute.value.name === 'not-found') {
        throw new Error(`${url}: não há vista para este endereço`)
      }
      const app = createSSRApp({ render: () => h(view) })
      app.use(router)
      html[url] = tidy(await renderToString(app))
    }
    return html
  } finally {
    await vite.close()
  }
}
