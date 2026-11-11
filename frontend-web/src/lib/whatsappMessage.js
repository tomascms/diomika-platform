/**
 * O texto do WhatsApp na página de um modelo (auditoria RP-13). O botão flutuante mandava sempre «Gostaria de obter mais
 * informações sobre o catálogo», também ao lado de um modelo, e cada conversa começava com «qual modelo?». Agora leva o
 * modelo, a cor e a medida escolhidas, o EAN e o endereço da página.
 */

/**
 * @param {{ name: string, category?: string, colour?: string, measureNoun?: string, measure?: string, ean?: string, url: string }} product
 *   `colour`: só se o modelo tiver mais do que uma cor (com uma só, «Sortido» não diz nada);
 *   `measureNoun`/`measure`: «medida» e «45x45 cm», «altura» e «32mm» (vazios nos artigos únicos)
 * @returns {string} «Olá! Gostaria de saber mais sobre o modelo Foglia (Almofada), cor Azul Ciano, medida 45x45 cm, EAN 5606044506574. https://…»
 */
export function productWhatsAppMessage({ name, category, colour, measureNoun, measure, ean, url }) {
  const model = category ? `${name} (${category})` : name
  const details = [
    colour && `cor ${colour}`,
    measure && `${measureNoun || 'medida'} ${measure}`,
    ean && `EAN ${ean}`,
  ].filter(Boolean)
  return `Olá! Gostaria de saber mais sobre o modelo ${model}${details.map((part) => `, ${part}`).join('')}. ${url}`
}
