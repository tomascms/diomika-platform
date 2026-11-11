import JSZip from 'jszip'

// Etiqueta Brother (P-touch Editor, .lbx) para a QL-700, fita de 29 mm. O papel, as margens e a impressora são os do
// modelo que o cliente acertou (src/assets/etiqueta/label.xml); o conteúdo é uma só imagem a 300 DPI desenhada em
// etiquetaImagem.js com o mesmo desenho, do tamanho exacto da área imprimível. Os objetos do P-touch (texto, QR,
// código de barras) mudavam de tamanho com os dados e saíam da fita; uma imagem não muda.

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

/** label.xml do modelo com um só objeto: a imagem `Object0.bmp`, do tamanho e no sítio da área imprimível. */
export function singleImageXml(labelXml) {
  const area = labelXml.match(/<style:backGround x="([\d.]+)pt" y="([\d.]+)pt" width="([\d.]+)pt" height="([\d.]+)pt"/)
  const image = labelXml.match(/<image:image>[\s\S]*?<\/image:image>/)
  if (!area || !image) throw new Error('Modelo de etiqueta sem área imprimível ou sem imagem.')
  const [, x, y, w, h] = area
  const box = `x="${x}pt" y="${y}pt" width="${w}pt" height="${h}pt"`
  const block = image[0]
    .replace(/(<pt:objectStyle )x="[^"]*" y="[^"]*" width="[^"]*" height="[^"]*"/, `$1${box}`)
    .replace(/(<image:orgPos )x="[^"]*" y="[^"]*" width="[^"]*" height="[^"]*"/, `$1${box}`)
    .replace(/objectName="[^"]*"/, 'objectName="Etiqueta"')
  return labelXml.replace(/<pt:objects>[\s\S]*<\/pt:objects>/, () => `<pt:objects>${block}</pt:objects>`)
}

/**
 * O .lbx (bytes de um zip): o papel do modelo e a etiqueta já desenhada (BMP de 1 bit, 300 DPI).
 * @param {object} args  { labelXml, propXml, labelBmp }
 */
export async function buildLabelLbx({ labelXml, propXml, labelBmp }) {
  const zip = new JSZip()
  zip.file('label.xml', singleImageXml(labelXml))
  zip.file('Object0.bmp', labelBmp)
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
