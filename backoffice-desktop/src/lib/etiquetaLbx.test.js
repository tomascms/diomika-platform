import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import JSZip from 'jszip'
import {
  buildProductLabelLbx,
  captionFit,
  wrapWords,
  dataUrlToBytes,
  ean12,
  labelCaption,
  labelFileName,
  modelPageUrl,
  setObjectData,
  SITE_HOME_URL,
} from './etiquetaLbx.js'

const here = dirname(fileURLToPath(import.meta.url))
const assets = join(here, '..', 'assets', 'etiqueta')
const load = (name) => readFileSync(join(assets, name))
const template = load('label.xml').toString('utf8')
const propXml = load('prop.xml').toString('utf8')
const logoBmp = load('Object0.bmp')

const product = {
  ean: '699903000800',
  caption: 'Cintos - Extensivel - 140x200',
  productUrl: 'https://www.diomika.com/categoria/cintos/extensivel',
  madeIn: 'Portugal',
}

async function build(overrides = {}) {
  const bytes = await buildProductLabelLbx({ templateXml: template, propXml, logoBmp, ...product, ...overrides })
  const zip = await JSZip.loadAsync(bytes)
  return {
    zip,
    xml: await zip.file('label.xml').async('string'),
    bmp: Buffer.from(await zip.file('Object0.bmp').async('uint8array')),
  }
}

/** Valor do <pt:data> do objeto, e o charLen da sua stringItem se for texto. */
function dataOf(xml, name) {
  const start = xml.indexOf(`objectName="${name}"`)
  const data = xml.slice(xml.indexOf('<pt:data>', start) + 9, xml.indexOf('</pt:data>', start))
  const next = xml.indexOf('<text:stringItem charLen="', start)
  const end = xml.indexOf('</text:text>', start)
  const charLen = next > -1 && (end < 0 || next < end) ? Number(xml.slice(next).match(/charLen="(\d+)"/)[1]) : null
  return { data, charLen }
}

test('o .lbx tem os três ficheiros e o papel do modelo do cliente, sem alterações', async () => {
  const { zip, xml } = await build()
  assert.deepEqual(Object.keys(zip.files).sort(), ['Object0.bmp', 'label.xml', 'prop.xml'])
  assert.equal(xml.match(/<style:paper[^>]*>/)[0], template.match(/<style:paper[^>]*>/)[0])
  // mesmos objetos que o modelo (nenhum acrescentado nem removido)
  const count = (s) => (s.match(/objectName="/g) || []).length
  assert.equal(count(xml), count(template))
})

test('os dados de cada produto ficam nos objetos certos', async () => {
  const { xml } = await build()
  assert.deepEqual(dataOf(xml, 'Text4'), { data: product.caption, charLen: product.caption.length })
  assert.deepEqual(dataOf(xml, 'Texto7'), { data: 'Made in Portugal', charLen: 'Made in Portugal'.length })
  assert.equal(dataOf(xml, 'Barcode').data, '699903000800')
  assert.equal(dataOf(xml, 'QR produto').data, product.productUrl)
  // a loja continua a ser a do modelo
  assert.equal(dataOf(xml, 'QR loja').data, SITE_HOME_URL)
})

test('a legenda ajusta-se à caixa (LONGTEXTAUTO); o «Made in» mantém o controlo do modelo', async () => {
  const { xml } = await build({ caption: 'Protetor de Colchão - Protetor Impermeável Extra - 200x200' })
  const block = (src, name) => {
    const start = src.indexOf(`objectName="${name}"`)
    return src.slice(start, src.indexOf('</text:text>', start))
  }
  assert.match(block(xml, 'Text4'), /control="LONGTEXTAUTO"/)
  assert.equal(block(xml, 'Texto7').match(/control="[^"]+"/)[0], block(template, 'Texto7').match(/control="[^"]+"/)[0])
  // a caixa da legenda: entre o logo (acaba em y 60) e o código de barras (começa em y 78,4)
  assert.ok(xml.includes('<pt:objectStyle x="10.4pt" y="61pt" width="66.1pt" height="16.5pt"'))
})

test('o logo é o do modelo (Object0.bmp)', async () => {
  const { bmp } = await build()
  assert.deepEqual(bmp, logoBmp)
})

test('sem «Made in» não há etiqueta: falha em vez de sair incompleta', async () => {
  await assert.rejects(build({ madeIn: '  ' }), /Made in/)
})

test('caracteres especiais ficam escapados no XML', async () => {
  const { xml } = await build({ caption: 'Cintos & Fivela <grande> - "Extensível"' })
  assert.equal(dataOf(xml, 'Text4').data, 'Cintos &amp; Fivela &lt;grande&gt; - &quot;Extensível&quot;')
  assert.doesNotThrow(() => JSON.stringify(setObjectData(template, 'Text4', 'a<b')))
})

test('EAN-13: 12 dígitos, a impressora calcula o controlo', () => {
  assert.equal(ean12('5604950046085'), '560495004608')
  assert.throws(() => ean12('123'), /EAN inválido/)
})

test('legenda «categoria - modelo - dimensão», sem partes vazias', () => {
  assert.equal(labelCaption({ categoryName: 'Cintos', modelName: 'Extensivel', dimension: '' }), 'Cintos - Extensivel')
  assert.equal(labelCaption({ categoryName: 'Passadeira', modelName: 'TRAPO', dimension: '50x150' }), 'Passadeira - TRAPO - 50x150')
})

test('nome do ficheiro', () => {
  assert.equal(labelFileName('Extensivel', '8394671571887'), 'etiqueta-extensivel-8394671571887.lbx')
  assert.equal(labelFileName('Extensível Pele', '8394671571887'), 'etiqueta-extensivel-pele-8394671571887.lbx')
})

test('logo embutido (data URL) lê-se sem fetch', () => {
  const bytes = dataUrlToBytes(`data:image/bmp;base64,${logoBmp.toString('base64')}`)
  assert.deepEqual(Buffer.from(bytes), logoBmp)
  assert.throws(() => dataUrlToBytes('https://x/y.bmp'), /Logo/)
})

test('link do QR do produto abre na dimensão da etiqueta (?ean=)', () => {
  assert.equal(
    modelPageUrl({ categoryName: 'Passadeira', modelName: 'TRAPO', ean: '5606044501319' }),
    'https://www.diomika.com/categoria/passadeira/trapo?ean=5606044501319',
  )
  assert.equal(modelPageUrl({ categoryName: '', modelName: 'TRAPO', ean: '1' }), null)
})

test('a legenda cabe sempre em 1 ou 2 linhas dentro da caixa, sem sair da largura', () => {
  for (const caption of ['Cintos - Cinto Extensivel', 'Protetor de Colchão - Protetor Impermeável Extra - 200x200', 'Cintos - Extensivel - 140x200']) {
    const { size } = captionFit(caption)
    assert.ok(size >= 4 && size <= 5.9, `${caption}: ${size}`)
    const lines = wrapWords(caption, Math.floor(66.1 / (0.42 * size)))
    assert.ok(lines.length <= 2, caption)
  }
  assert.equal(captionFit('Cintos - Cinto Extensivel').size, 5.9)
})
