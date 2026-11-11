import { test } from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'

// O aviso do backoffice (LEGAL-12): `CompositionField.vue` mostra um aviso por cada denominação que não é fibra do Anexo I
// do Reg. (UE) 1007/2011, e não impede nada. Renderiza o componente a sério (o Vite do backoffice carrega-o, o Vue
// renderiza-o) com uma composição e lê o HTML. Vive aqui, com a lista de fibras que o componente usa.
const BACKOFFICE = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '..',
  '..',
  'backoffice-desktop',
)

async function withComponent(run) {
  const vite = await createServer({
    root: BACKOFFICE,
    configFile: path.join(BACKOFFICE, 'vite.config.js'),
    appType: 'custom',
    logLevel: 'error',
    server: { middlewareMode: true, hmr: false, ws: false, watch: null },
    optimizeDeps: { noDiscovery: true, include: [] },
    // Um só Vue (o da loja, que este teste usa para renderizar): o componente do backoffice importa «vue» e recebe esse.
    ssr: { external: ['vue'] },
    resolve: {
      alias: { vue: path.dirname(fileURLToPath(import.meta.resolve('vue/package.json'))) },
    },
  })
  try {
    const { default: CompositionField } = await vite.ssrLoadModule(
      '/src/components/CompositionField.vue',
    )
    const render = (modelValue) =>
      renderToString(createSSRApp({ render: () => h(CompositionField, { modelValue }) }))
    return await run(render)
  } finally {
    await vite.close()
  }
}

const warnings = (html) =>
  [...html.matchAll(/<p class="fibre-warning"[^>]*>\s*([^<]*?)\s*<\/p>/g)].map((m) =>
    m[1].replace(/\s+/g, ' '),
  )

test('uma composição com «Veludo» mostra o aviso, e as fibras do Anexo I não', async () => {
  await withComponent(async (render) => {
    const veludo = warnings(await render({ Veludo: 100 }))
    assert.equal(veludo.length, 1)
    assert.match(
      veludo[0],
      /^«Veludo» não é uma denominação de fibra do Anexo I do Regulamento \(UE\) n\.º 1007\/2011\./,
    )
    assert.match(veludo[0], /Pode gravar na mesma\.$/)

    assert.deepEqual(warnings(await render({ Poliester: 100 })), [])
    assert.deepEqual(warnings(await render({ Poliéster: 60, Algodão: 40 })), [])
  })
})

test('avisa de cada denominação que não é do Anexo I, uma vez, e só dessas', async () => {
  await withComponent(async (render) => {
    const found = warnings(await render({ Poliéster: 50, Veludo: 30, Malha: 20 }))

    assert.equal(found.length, 2)
    assert.ok(found[0].startsWith('«Veludo»') && found[1].startsWith('«Malha»'))
  })
})

test('o aviso não bloqueia: o total e a soma continuam lá e não há campo obrigatório nem botão desactivado por causa dele', async () => {
  await withComponent(async (render) => {
    const html = await render({ Veludo: 100 })

    assert.match(html, /Total a gravar: 100%/)
    assert.doesNotMatch(html, /required|disabled/)
  })
})
