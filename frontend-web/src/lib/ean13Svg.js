// Código de barras EAN-13 desenhado em SVG (vetor): nítido em qualquer tamanho, sem imagem. Usa-se no catálogo
// para imprimir. Tudo em módulos (1 módulo = 1 barra fina): a largura total é 95 módulos + zonas de silêncio.

const L = ['0001101', '0011001', '0010011', '0111101', '0100011', '0110001', '0101111', '0111011', '0110111', '0001011']
const G = ['0100111', '0110011', '0011011', '0100001', '0011101', '0111001', '0000101', '0010001', '0001001', '0010111']
const R = ['1110010', '1100110', '1101100', '1000010', '1011100', '1001110', '1010000', '1000100', '1001000', '1110100']
// Padrão L/G do primeiro dígito (os seis seguintes).
const PARITY = ['LLLLLL', 'LLGLGG', 'LLGGLG', 'LLGGGL', 'LGLLGG', 'LGGLLG', 'LGGGLL', 'LGLGLG', 'LGLGGL', 'LGGLGL']

const QUIET_LEFT = 9
const QUIET_RIGHT = 9
const BAR_HEIGHT = 69 // módulos de altura das barras normais
const GUARD_HEIGHT = 74 // as barras de guarda descem um pouco mais
const DIGITS_BASELINE = 78

/** Dígito de controlo EAN-13 dos 12 primeiros dígitos. */
export function ean13Check(twelve) {
  const sum = [...twelve].reduce((acc, d, i) => acc + Number(d) * (i % 2 === 0 ? 1 : 3), 0)
  return String((10 - (sum % 10)) % 10)
}

/** EAN-13 válido (13 dígitos e dígito de controlo certo), ou null. */
export function validEan13(value) {
  const ean = String(value ?? '').replace(/\s+/g, '')
  if (!/^\d{13}$/.test(ean)) return null
  return ean13Check(ean.slice(0, 12)) === ean[12] ? ean : null
}

/** Sequência de 95 módulos (1 = barra, 0 = espaço) do EAN-13. */
export function ean13Bits(ean) {
  if (!validEan13(ean)) throw new Error(`EAN inválido: «${ean}».`)
  const first = Number(ean[0])
  const pattern = PARITY[first]
  let bits = '101'
  for (let i = 1; i <= 6; i += 1) {
    const d = Number(ean[i])
    bits += pattern[i - 1] === 'L' ? L[d] : G[d]
  }
  bits += '01010'
  for (let i = 7; i <= 12; i += 1) bits += R[Number(ean[i])]
  bits += '101'
  return bits
}

/**
 * Desenho do código como dados (sem HTML): barras e textos em módulos, para o template do Vue os pintar sem `v-html`.
 * Devolve null se o EAN não for válido.
 */
export function ean13Drawing(value) {
  const ean = validEan13(value)
  if (!ean) return null
  const bits = ean13Bits(ean)
  const bars = []
  let run = null
  for (let i = 0; i <= bits.length; i += 1) {
    const on = bits[i] === '1'
    if (on && run === null) run = i
    if (!on && run !== null) {
      const guard = (run < 3) || (i > 45 && i < 50) || (i >= 92)
      bars.push({ x: QUIET_LEFT + run, width: i - run, height: guard ? GUARD_HEIGHT : BAR_HEIGHT })
      run = null
    }
  }
  const digit = (x, text) => ({ x, text })
  const texts = [digit(QUIET_LEFT / 2, ean[0])]
  for (let i = 0; i < 6; i += 1) texts.push(digit(QUIET_LEFT + 3 + 7 * i + 3.5, ean[1 + i]))
  for (let i = 0; i < 6; i += 1) texts.push(digit(QUIET_LEFT + 3 + 42 + 5 + 7 * i + 3.5, ean[7 + i]))
  return {
    ean,
    viewBox: `0 0 ${QUIET_LEFT + 95 + QUIET_RIGHT} 79`,
    baseline: DIGITS_BASELINE,
    bars,
    texts,
  }
}

/** SVG do código como texto (para testes e usos fora do Vue): viewBox em módulos, sem largura nem altura fixas. */
export function ean13Svg(value) {
  const d = ean13Drawing(value)
  if (!d) return null
  const bars = d.bars.map((b) => `<rect x="${b.x}" y="0" width="${b.width}" height="${b.height}"/>`).join('')
  const texts = d.texts
    .map((t) => `<text x="${t.x}" y="${d.baseline}" text-anchor="middle">${t.text}</text>`)
    .join('')
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${d.viewBox}" role="img" aria-label="EAN ${d.ean}">` +
    `<g fill="#000">${bars}</g>` +
    `<g font-family="Arial, Helvetica, sans-serif" font-size="9" fill="#000">${texts}</g>` +
    '</svg>'
  )
}
