import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import JSZip from 'jszip'
import { buildLabelLbx, ean12, labelCaption, labelFileName, SITE_HOME_URL } from './etiquetaLbx.js'
import { AREA, DPI, drawLabel, ean13Bars, HEIGHT, LAYOUT, qrFit, rgbaToBmp1, WIDTH } from './etiquetaImagem.js'

const here = dirname(fileURLToPath(import.meta.url))
const assets = join(here, '..', 'assets', 'etiqueta')
const load = (name) => readFileSync(join(assets, name))
const template = load('label.xml').toString('utf8')
const LONG_URL = 'https://www.diomika.com/categoria/protetores-colchao/protetor-de-colchao-impermeavel-extra?ean=5604950046085'

async function build() {
  const labelBmp = rgbaToBmp1(new Uint8ClampedArray(WIDTH * HEIGHT * 4).fill(255), WIDTH, HEIGHT)
  const bytes = await buildLabelLbx({ labelXml: template, propXml: load('prop.xml').toString('utf8'), labelBmp })
  const zip = await JSZip.loadAsync(bytes)
  return { zip, xml: await zip.file('label.xml').async('string'), bmp: Buffer.from(await zip.file('Object0.bmp').async('uint8array')) }
}

/** Contexto falso: guarda cada retângulo e cada texto, para ver que tudo fica dentro da imagem. */
function fakeCtx() {
  const marks = []
  const ctx = {
    marks,
    font: '',
    fillRect: (x, y, w, h) => marks.push({ x, y, w, h }),
    fillText: (text, x, y, max) => marks.push({ text, x, y, max }),
    measureText: (text) => ({ width: [...text].length * Number.parseFloat(ctx.font) * 0.55 }),
    drawImage: (img, x, y, w, h) => marks.push({ x, y, w, h, image: true }),
  }
  return ctx
}

test('o .lbx tem o papel do modelo e um só objeto: a imagem do tamanho da área imprimível', async () => {
  const { zip, xml } = await build()
  assert.deepEqual(Object.keys(zip.files).sort(), ['Object0.bmp', 'label.xml', 'prop.xml'])
  assert.equal(xml.match(/<style:paper[^>]*>/)[0], template.match(/<style:paper[^>]*>/)[0])
  assert.equal((xml.match(/<(text:text|barcode:barcode|image:image)>/g) || []).length, 1)
  const box = `x="${AREA.x}pt" y="${AREA.y}pt" width="${AREA.width}pt" height="${AREA.height}pt"`
  assert.ok(xml.includes(`<pt:objectStyle ${box}`))
  assert.ok(xml.includes(`<image:orgPos ${box}`))
})

// O P-touch imprime o BMP com o tamanho físico dele (píxeis ÷ DPI): tem de ser o da área imprimível.
test('o BMP é de 1 bit, a 300 DPI, com o tamanho físico da área imprimível', async () => {
  const { bmp } = await build()
  const ptOf = (px, ppm) => (px / (ppm * 0.0254)) * 72
  assert.equal(bmp.readUInt16LE(28), 1)
  assert.equal(Math.round(bmp.readInt32LE(38) * 0.0254), DPI)
  assert.ok(Math.abs(ptOf(bmp.readInt32LE(18), bmp.readInt32LE(38)) - AREA.width) < 0.3)
  assert.ok(Math.abs(ptOf(bmp.readInt32LE(22), bmp.readInt32LE(42)) - AREA.height) < 0.3)
})

test('tudo o que se desenha fica dentro da área, mesmo com nomes e links compridos', () => {
  const ctx = fakeCtx()
  drawLabel(ctx, {
    ean: '5604950046085',
    caption: 'Protetor de Colchão - Protetor de Colchão Impermeável Extra Grande - 200x200',
    shopUrl: SITE_HOME_URL,
    productUrl: LONG_URL,
    madeIn: 'República Popular da China',
    logo: {},
  })
  for (const m of ctx.marks) {
    if (m.text !== undefined) {
      assert.ok((m.max ?? 0) <= WIDTH && m.x > 0 && m.x < WIDTH && m.y >= 0 && m.y <= HEIGHT, `texto fora: ${m.text}`)
    } else {
      assert.ok(m.x >= 0 && m.y >= 0 && m.x + m.w <= WIDTH && m.y + m.h <= HEIGHT, `fora: ${JSON.stringify(m)}`)
    }
  }
})

test('as zonas não se sobrepõem e o QR do produto cabe na sua', () => {
  const L = LAYOUT
  assert.ok(L.shopQr.y + L.shopQr.max <= L.logo.y)
  assert.ok(L.logo.y + L.logo.height <= L.caption.y)
  assert.ok(L.caption.y + L.caption.height <= L.barcode.y)
  assert.ok(L.barcode.y + L.barcode.bars + 30 <= L.productQr.y) // barras, guardas e números
  assert.ok(L.productQr.y + L.productQr.max <= L.madeIn.y)
  assert.ok(L.madeIn.y + L.madeIn.height <= HEIGHT)
  assert.ok(qrFit(LONG_URL, L.productQr.max).size <= L.productQr.max)
  assert.ok(95 * L.barcode.module <= WIDTH)
})

test('EAN-13: 95 barras, com o dígito de controlo verificado', () => {
  const bars = ean13Bars('5604950046085')
  assert.equal(bars.length, 95)
  assert.ok(bars.startsWith('101') && bars.endsWith('101') && bars.slice(45, 50) === '01010')
  // 4006381333931 é o exemplo da norma: começa por L(0)=0001101 depois de 101.
  assert.equal(ean13Bars('4006381333931').slice(3, 10), '0001101')
  assert.throws(() => ean13Bars('5604950046086'), /controlo/)
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

test('logo embutido (data URL) lê-se sem fetch', async () => {
  const { dataUrlToBytes } = await import('./etiquetaLbx.js')
  const original = load('Object0.bmp')
  const bytes = dataUrlToBytes(`data:image/bmp;base64,${original.toString('base64')}`)
  assert.deepEqual(Buffer.from(bytes), original)
  assert.throws(() => dataUrlToBytes('https://x/y.bmp'), /Logo/)
})

test('link do QR do produto abre na dimensão da etiqueta (?ean=)', async () => {
  const { modelPageUrl } = await import('./etiquetaLbx.js')
  assert.equal(
    modelPageUrl({ categoryName: 'Passadeira', modelName: 'TRAPO', ean: '5606044501319' }),
    'https://www.diomika.com/categoria/passadeira/trapo?ean=5606044501319',
  )
  assert.equal(modelPageUrl({ categoryName: '', modelName: 'TRAPO', ean: '1' }), null)
})
