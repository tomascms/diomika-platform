/**
 * Avisos sobre uma fotografia antes de a gravar (RP-11). A loja mostra a imagem num quadrado (`aspect-ratio: 1`,
 * `object-fit: cover`) e a 1200 px de lado; abaixo disso fica mole, e uma foto comprida perde as pontas.
 * Avisa, não impede: o servidor só recusa o que é perigoso (tamanho e formato).
 */
export const MIN_SIDE = 1200
const MAX_RATIO = 1.25 // 5:4; mais comprida que isto perde mais de um quinto no recorte quadrado

export function imageWarnings(width, height) {
  if (!(width > 0 && height > 0)) return []
  const out = []
  if (Math.min(width, height) < MIN_SIDE) {
    out.push(`Imagem pequena (${width}×${height}): use pelo menos ${MIN_SIDE} px de lado, senão fica desfocada na loja.`)
  }
  const ratio = Math.max(width, height) / Math.min(width, height)
  if (ratio > MAX_RATIO) {
    out.push(`Proporção ${width}×${height}: a loja mostra a foto num quadrado e corta as pontas. Prefira uma foto quadrada.`)
  }
  return out
}
