/**
 * A linha do pedido para um artigo (um EAN numa cor), igual venha da ficha do produto ou do pedido rápido (RP-14).
 * Era montada à mão na ficha; duas vias para a mesma coisa é como nasceram FE-01 e FE-10.
 */
import { resolveCartQtyRules } from './quantity.js'
import { isSingleProductMode } from './storefrontFormat.js'

/**
 * @param {object} args
 * @param {object} args.model     o modelo como a API o manda (com `_storefront`)
 * @param {object} args.category  a categoria do modelo (`carrinho_step`, `carrinho_min`)
 * @param {object} args.product   a linha de produto (a variante com o EAN)
 * @param {object} args.color     a cor (`numero`, `nome`)
 * @param {number} args.quantity
 * @param {string} [args.image]   o URL da imagem da cor, para a miniatura do pedido
 */
export function cartItemFor({ model, category, product, color, quantity, image = '' }) {
  const ctx = model._storefront
  const rules = resolveCartQtyRules(category)
  return {
    ean: product.ean,
    numero_cor: color.numero,
    // `altura` na API é texto: só as alturas dos assentos («32mm»); nos artigos únicos não há.
    altura: typeof product.altura === 'string' && product.altura ? product.altura : undefined,
    quantidade: quantity,
    modeloNome: model.nome,
    // A medida de cada variante («45x45», «32mm»); um artigo único não tem medida («Referência» não é uma).
    dimensoes: isSingleProductMode(ctx) ? '' : (product[ctx?.picker?.field || 'dimensoes'] ?? ''),
    corNome: color.nome,
    carrinhoStep: rules.step,
    carrinhoMin: rules.min,
    imagem: image,
  }
}
