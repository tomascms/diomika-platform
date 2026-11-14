import JSZip from 'jszip'

// Etiqueta Brother (P-touch Editor, .lbx) para a QL-700. O modelo é o que o cliente desenhou
// (src/assets/etiqueta/label.xml): o papel, as margens, o logo e todos os objetos (texto, código de barras, QR)
// ficam como estão; só se trocam os dados de cada produto: legenda, EAN, QR do produto e «Made in».

export const SITE_HOME_URL = 'https://www.diomika.com'

export function xmlEscape(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

/** EAN-13 → os 12 primeiros dígitos (o dígito de controlo é calculado pela impressora). */
export function ean12(ean) {
  const digits = String(ean || '').replace(/\D/g, '')
  if (digits.length < 12) throw new Error(`EAN inválido para etiqueta: «${ean}».`)
  return digits.slice(0, 12)
}

/** «categoria - modelo - dimensão», sem partes vazias. */
export function labelCaption({ categoryName = '', modelName = '', dimension = '' }) {
  return [categoryName, modelName, dimension].map((v) => String(v || '').trim()).filter(Boolean).join(' - ')
}

// Caixa da legenda: x 10,4 pt, largura 66,1 pt. Por cima está o logo (acaba em y 60 pt) e por baixo o código de
// barras (começa em y 78,4 pt); a caixa vai de y 61 a y 77,5 pt e o texto fica centrado nela. Cabe numa linha ou em duas.
const CAPTION_WIDTH = 66.1
const CAPTION_TOP = 61
const CAPTION_HEIGHT = 16.5
const CAPTION_MAX_SIZE = 5.9
const CAPTION_MIN_SIZE = 4
const CAPTION_LINE_HEIGHT = 1.2

/** Quebra o texto por palavras em linhas de no máximo `chars` caracteres. */
export function wrapWords(text, chars) {
  const lines = []
  let line = ''
  for (const word of String(text).split(/\s+/).filter(Boolean)) {
    const next = line ? `${line} ${word}` : word
    if (next.length <= chars || !line) line = next
    else {
      lines.push(line)
      line = word
    }
  }
  if (line) lines.push(line)
  return lines
}

/** Tamanho da legenda: o maior que deixa o texto em 1 ou 2 linhas dentro da caixa. */
export function captionFit(text) {
  const charWidth = 0.42 // largura média de um carácter, em múltiplos do tamanho (Helsinki/Arial)
  for (let size = CAPTION_MAX_SIZE; size >= CAPTION_MIN_SIZE - 1e-9; size = Math.round((size - 0.1) * 10) / 10) {
    const chars = Math.floor(CAPTION_WIDTH / (charWidth * size))
    const lines = wrapWords(text, chars).length
    if (lines <= 2 && lines * CAPTION_LINE_HEIGHT * size <= CAPTION_HEIGHT) return { size }
  }
  return { size: CAPTION_MIN_SIZE }
}

/**
 * Troca os dados de um objeto do label.xml (o `<pt:data>` que vem a seguir ao seu nome).
 * Nos textos, o `charLen` acompanha o comprimento; com `autoFit` (só a legenda) o texto ajusta-se à caixa (LONGTEXTAUTO).
 */
export function setObjectData(xml, name, value, { isText = false, autoFit = false } = {}) {
  const start = xml.indexOf(`objectName="${name}"`)
  if (start < 0) throw new Error(`Modelo de etiqueta sem o objeto «${name}».`)
  const open = xml.indexOf('<pt:data>', start)
  const close = xml.indexOf('</pt:data>', open)
  if (open < 0 || close < 0) throw new Error(`Objeto «${name}» sem dados.`)
  const text = String(value)
  let out = xml.slice(0, open + '<pt:data>'.length) + xmlEscape(text) + xml.slice(close)
  if (isText) {
    const end = out.indexOf('</text:text>', start)
    let block = out.slice(start, end)
    if (autoFit) block = block.replace(/control="[^"]+"/, 'control="LONGTEXTAUTO"')
    block = block.replace(/(<text:stringItem charLen=")\d+(")/, `$1${[...text].length}$2`)
    out = out.slice(0, start) + block + out.slice(end)
  }
  return out
}

/** Tamanho da fonte e caixa da legenda (x e largura são os do modelo). */
export function setCaptionBox(xml, { size }) {
  const start = xml.indexOf('objectName="Text4"')
  if (start < 0) throw new Error('Modelo de etiqueta sem a legenda (Text4).')
  const end = xml.indexOf('</text:text>', start)
  let block = xml.slice(start, end).replace(/size="[^"]+"/g, `size="${size}pt"`)
  const box = xml.lastIndexOf('<pt:objectStyle', start)
  const boxEnd = xml.indexOf('>', box)
  const style = xml
    .slice(box, boxEnd)
    .replace(/ y="[^"]+"/, ` y="${CAPTION_TOP}pt"`)
    .replace(/height="[^"]+"/, `height="${CAPTION_HEIGHT}pt"`)
  return xml.slice(0, box) + style + xml.slice(boxEnd, start) + block + xml.slice(end)
}

/**
 * O .lbx de um produto (bytes de um zip).
 * @param {object} args  { templateXml, propXml, logoBmp, ean, caption, productUrl, madeIn }
 *   logoBmp: bytes do logo (Object0.bmp do modelo). Falta o «Made in» → erro, para não sair uma etiqueta incompleta.
 */
export async function buildProductLabelLbx({ templateXml, propXml, logoBmp, ean, caption, productUrl, madeIn }) {
  if (!String(madeIn || '').trim()) throw new Error('Falta o «Made in» (país de fabrico) no modelo.')
  let xml = templateXml
  // A legenda ajusta-se à caixa (entre o logo e o código de barras): tamanho variável, sempre dentro das margens.
  xml = setObjectData(xml, 'Text4', caption, { isText: true, autoFit: true })
  xml = setCaptionBox(xml, captionFit(caption))
  xml = setObjectData(xml, 'Texto7', `Made in ${String(madeIn).trim()}`, { isText: true })
  xml = setObjectData(xml, 'Barcode', ean12(ean))
  xml = setObjectData(xml, 'QR produto', productUrl)
  const zip = new JSZip()
  zip.file('label.xml', xml)
  zip.file('Object0.bmp', logoBmp)
  zip.file('prop.xml', propXml)
  return zip.generateAsync({ type: 'uint8array', compression: 'DEFLATE' })
}

/** Nome do ficheiro: etiqueta-<modelo>-<EAN>.lbx */
export function labelFileName(modelName, ean) {
  const base = slugify(modelName) || 'produto'
  return `etiqueta-${base}-${String(ean || '').replace(/\D/g, '')}.lbx`
}

/** Slug legível para URL, igual ao da loja (sem acentos, só a-z0-9 e hífens). */
export function slugify(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

/**
 * Página do modelo na loja: /categoria/<categoria>/<modelo>. Com `ean`, junta ?ean=<EAN> e a loja abre já nesse
 * produto (dimensão/variante da etiqueta). null se faltar a categoria ou o modelo.
 */
export function modelPageUrl({ categoryName, modelName, ean = '' }) {
  const cat = slugify(categoryName)
  const model = slugify(modelName)
  if (!cat || !model) return null
  const digits = String(ean || '').replace(/\D/g, '')
  return `${SITE_HOME_URL}/categoria/${cat}/${model}${digits ? `?ean=${digits}` : ''}`
}

/** Bytes de um data URL (base64). Sem fetch: a política da app não deixa fetch a data: URLs. */
export function dataUrlToBytes(dataUrl) {
  const match = String(dataUrl || '').match(/^data:[^;,]*;base64,(.*)$/)
  if (!match) throw new Error('Logo da etiqueta inválido.')
  const binary = atob(match[1])
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i)
  return bytes
}
