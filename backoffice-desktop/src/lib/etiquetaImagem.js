import QRCode from 'qrcode'

// A etiqueta inteira desenhada aqui, ponto a ponto a 300 DPI (a resolução da QL-700), e posta no .lbx como uma só
// imagem com o tamanho físico da área imprimível. O P-touch imprime-a tal e qual: nada se mexe, nada se corta,
// seja qual for o comprimento do link ou do nome. O desenho é o que o cliente acertou no P-touch Editor (2026-11-10):
// QR da loja em cima à esquerda, logo, «categoria - modelo - dimensão», EAN, QR do produto e «Fabricado em …».

export const DPI = 300
export const pt = (value) => Math.round((value * DPI) / 72) // pontos tipográficos → pontos da impressora

// Área imprimível do modelo (style:backGround do label.xml): é o tamanho da imagem.
export const AREA = { x: 4.3, y: 8.4, width: 73.5, height: 158.9 }
export const WIDTH = pt(AREA.width)
export const HEIGHT = pt(AREA.height)

const L = {
  shopQr: { x: pt(0.4), y: pt(0.3), max: pt(21) },
  logo: { x: pt(9), y: pt(26.3), width: pt(56.6), height: pt(32) },
  caption: { y: pt(59), height: pt(12.5), font: 5.4 },
  barcode: { y: pt(72), bars: pt(24), module: 3, font: 6 },
  productQr: { y: pt(106), max: pt(40) },
  madeIn: { y: pt(148), height: pt(10), font: 7 },
}
export const LAYOUT = L

const EAN_L = ['0001101', '0011001', '0010011', '0111101', '0100011', '0110001', '0101111', '0111011', '0110111', '0001011']
const EAN_PARITY = ['LLLLLL', 'LLGLGG', 'LLGGLG', 'LLGGGL', 'LGLLGG', 'LGGLLG', 'LGGGLL', 'LGLGLG', 'LGLGGL', 'LGGLGL']
const invert = (bits) => [...bits].map((b) => (b === '1' ? '0' : '1')).join('')

/** EAN-13 válido (com o dígito de controlo certo) → as 95 barras ('1' = preta). */
export function ean13Bars(ean) {
  const d = String(ean || '').replace(/\D/g, '')
  if (d.length !== 13) throw new Error(`EAN inválido para etiqueta: «${ean}».`)
  const sum = [...d.slice(0, 12)].reduce((s, c, i) => s + Number(c) * (i % 2 ? 3 : 1), 0)
  if ((10 - (sum % 10)) % 10 !== Number(d[12])) throw new Error(`EAN com o dígito de controlo errado: «${ean}».`)
  const parity = EAN_PARITY[Number(d[0])]
  let bars = '101'
  for (let i = 1; i <= 6; i += 1) {
    const l = EAN_L[Number(d[i])]
    bars += parity[i - 1] === 'L' ? l : [...invert(l)].reverse().join('')
  }
  bars += '01010'
  for (let i = 7; i <= 12; i += 1) bars += invert(EAN_L[Number(d[i])])
  return `${bars}101`
}

/** Matriz do QR (nível M) e o tamanho de cada módulo em pontos inteiros, o maior que cabe em `max` com 2 de margem. */
export function qrFit(text, max) {
  const { modules } = QRCode.create(String(text), { errorCorrectionLevel: 'M' })
  const cell = Math.floor(max / (modules.size + 4))
  if (cell < 3) throw new Error('O link do QR é demasiado comprido para a etiqueta.')
  return { modules, cell, size: modules.size * cell }
}

function drawQr(ctx, text, x, y, max) {
  const { modules, cell, size } = qrFit(text, max)
  for (let r = 0; r < modules.size; r += 1)
    for (let c = 0; c < modules.size; c += 1)
      if (modules.get(r, c)) ctx.fillRect(x + c * cell, y + r * cell, cell, cell)
  return size
}

/** Melhor corte em duas linhas (o que deixa a linha mais comprida mais curta), pelos espaços. */
function splitTwo(ctx, text) {
  const words = text.split(' ')
  let best = [text]
  let bestWidth = ctx.measureText(text).width
  for (let i = 1; i < words.length; i += 1) {
    const lines = [words.slice(0, i).join(' '), words.slice(i).join(' ')]
    const width = Math.max(...lines.map((l) => ctx.measureText(l).width))
    if (width < bestWidth) [best, bestWidth] = [lines, width]
  }
  return { lines: best, width: bestWidth }
}

/**
 * Texto centrado na zona: numa linha se couber; senão em duas (se `twoLines` e a zona tiver altura); senão encolhe
 * até caber (como o «shrink» do P-touch). Nunca passa da largura.
 */
function drawText(ctx, text, y, height, sizePt, family, twoLines = false) {
  if (!text) return
  const max = WIDTH - pt(1)
  let size = pt(sizePt)
  let lines = [text]
  for (; size > pt(3); size -= 1) {
    ctx.font = `${size}px ${family}`
    if (ctx.measureText(text).width <= max) {
      lines = [text]
      break
    }
    const two = twoLines && size * 2.3 <= height ? splitTwo(ctx, text) : null
    if (two && two.width <= max) {
      lines = two.lines
      break
    }
  }
  ctx.font = `${size}px ${family}`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  const lineHeight = size * 1.15
  const top = y + height / 2 - (lineHeight * (lines.length - 1)) / 2
  lines.forEach((line, i) => ctx.fillText(line, WIDTH / 2, top + i * lineHeight, max))
}

function drawBarcode(ctx, ean, family) {
  const bars = ean13Bars(ean)
  const m = L.barcode.module
  const digits = String(ean).replace(/\D/g, '')
  // 6 pontos brancos à direita, mais a margem da fita (4,4 pt): a zona livre de 7 módulos que os leitores pedem.
  const left = WIDTH - bars.length * m - 6
  const { y, bars: h } = L.barcode
  const guard = new Set([0, 1, 2, 45, 46, 47, 48, 49, 92, 93, 94])
  for (let i = 0; i < bars.length; i += 1)
    if (bars[i] === '1') ctx.fillRect(left + i * m, y, m, h + (guard.has(i) ? pt(3) : 0))
  ctx.font = `${pt(L.barcode.font)}px ${family}`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  const ty = y + h + pt(0.4)
  ctx.fillText(digits[0], left - pt(2.6), ty)
  for (let i = 0; i < 6; i += 1) ctx.fillText(digits[1 + i], left + (3 + 7 * i + 3.5) * m, ty)
  for (let i = 0; i < 6; i += 1) ctx.fillText(digits[7 + i], left + (50 + 7 * i + 3.5) * m, ty)
}

/**
 * Desenha a etiqueta num canvas WIDTH × HEIGHT (fundo branco, tinta preta).
 * @param {CanvasRenderingContext2D} ctx
 * @param {object} d  { ean, caption, shopUrl, productUrl, madeIn, logo (CanvasImageSource), family }
 */
export function drawLabel(ctx, { ean, caption, shopUrl, productUrl, madeIn = '', logo, family = 'sans-serif' }) {
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, WIDTH, HEIGHT)
  ctx.fillStyle = '#000'
  drawQr(ctx, shopUrl, L.shopQr.x, L.shopQr.y, L.shopQr.max)
  if (logo) ctx.drawImage(logo, L.logo.x, L.logo.y, L.logo.width, L.logo.height)
  drawText(ctx, caption, L.caption.y, L.caption.height, L.caption.font, family, true)
  drawBarcode(ctx, ean, family)
  const { size } = qrFit(productUrl, L.productQr.max)
  drawQr(ctx, productUrl, Math.round((WIDTH - size) / 2), L.productQr.y, L.productQr.max)
  if (madeIn) drawText(ctx, `Fabricado em ${madeIn}`, L.madeIn.y, L.madeIn.height, L.madeIn.font, family)
}

/** Píxeis RGBA → BMP de 1 bit (preto se mais escuro do que meio cinzento), com o DPI da impressora. */
export function rgbaToBmp1(rgba, width, height, dpi = DPI) {
  const rowBytes = Math.ceil(width / 32) * 4
  const offset = 14 + 40 + 8
  const out = new Uint8Array(offset + rowBytes * height)
  const v = new DataView(out.buffer)
  out[0] = 0x42
  out[1] = 0x4d
  v.setUint32(2, out.length, true)
  v.setUint32(10, offset, true)
  v.setUint32(14, 40, true)
  v.setInt32(18, width, true)
  v.setInt32(22, height, true)
  v.setUint16(26, 1, true)
  v.setUint16(28, 1, true)
  v.setUint32(34, rowBytes * height, true)
  const ppm = Math.round(dpi / 0.0254)
  v.setInt32(38, ppm, true)
  v.setInt32(42, ppm, true)
  v.setUint32(46, 2, true)
  out.set([0, 0, 0, 0, 255, 255, 255, 0], 54) // cor 0 preta, cor 1 branca
  for (let y = 0; y < height; y += 1) {
    const row = offset + (height - 1 - y) * rowBytes // BMP guarda as linhas de baixo para cima
    for (let x = 0; x < width; x += 1) {
      const i = (y * width + x) * 4
      const light = rgba[i + 3] < 128 || rgba[i] * 0.3 + rgba[i + 1] * 0.59 + rgba[i + 2] * 0.11 >= 128
      if (light) out[row + (x >> 3)] |= 0x80 >> (x & 7)
    }
  }
  return out
}

/** No navegador/Electron: desenha a etiqueta e devolve o BMP. `logoUrl` é o logo embutido (data URL). */
export async function renderLabelBmp({ logoUrl, family = '"Archivo Variable", Arial, sans-serif', ...data }) {
  const logo = new Image()
  logo.src = logoUrl
  await logo.decode()
  await document.fonts?.load?.(`${pt(6)}px ${family}`).catch(() => {})
  const canvas = document.createElement('canvas')
  canvas.width = WIDTH
  canvas.height = HEIGHT
  const ctx = canvas.getContext('2d')
  drawLabel(ctx, { ...data, logo, family })
  return { bmp: rgbaToBmp1(ctx.getImageData(0, 0, WIDTH, HEIGHT).data, WIDTH, HEIGHT), canvas }
}
