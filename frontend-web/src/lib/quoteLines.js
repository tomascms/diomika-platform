/**
 * Linhas do carrinho → linhas do pedido de orçamento (PedidoOrcamentoLinha na API).
 * `altura` na API é texto (máx. 32): só segue se for texto não vazio. Carrinhos
 * guardados no browser antes desta correcção podem trazer o produto inteiro
 * (objecto) nos modos «unico»/«leitura», e a API recusava o pedido com 422.
 */
export const toQuoteLines = (items) =>
  items.map(({ ean, numero_cor, quantidade, altura }) => ({
    ean,
    numero_cor: Number(numero_cor),
    quantidade: Number(quantidade),
    ...(typeof altura === 'string' && altura ? { altura } : {}),
  }))

/** Chave de uma linha do carrinho: EAN, cor e altura (texto). */
export const itemKey = (item) => `${item.ean}|${item.numero_cor}|${item.altura || ''}`

/**
 * Carrinho lido do browser → carrinho coerente. Linhas guardadas antes da correcção
 * acima podem ter `altura` como objecto (o produto inteiro): remove-se, e as linhas que
 * passam a ter a mesma chave (EAN, cor, altura) juntam-se numa só, somando as quantidades.
 * Função pura: não altera o carrinho de entrada.
 */
export const normalizeCartItems = (items) => {
  const byKey = new Map()
  for (const item of items) {
    const { altura, ...rest } = item
    const clean = typeof altura === 'string' && altura ? { ...rest, altura } : rest
    const key = itemKey(clean)
    const seen = byKey.get(key)
    // Soma como números (nunca concatena texto); a linha mais recente dá os dados, a primeira dá a posição.
    const quantidade = seen
      ? (Number(seen.quantidade) || 0) + (Number(clean.quantidade) || 0)
      : clean.quantidade
    byKey.set(key, seen ? { ...seen, ...clean, quantidade } : clean)
  }
  return [...byKey.values()]
}

/** O que está no pedido, em artigos e em unidades: «1 artigo · 12 un.», «2 artigos · 72 un.» (RP-17). */
export const cartSummaryText = ({ lines, units }) =>
  `${lines} ${lines === 1 ? 'artigo' : 'artigos'} · ${units} un.`

/**
 * Segunda linha de um artigo no pedido: a medida (só se for uma medida) e a cor.
 * «Referência» e «Sortido» (artigos únicos) não são medidas e não se mostram; sem altura, a medida leva « cm».
 * «45x45 cm · Cor 12 (Azul Ciano)», «32mm · Cor 1 (Sortido)», «Cor 1 (Sortido)».
 */
export const lineMeta = (item) =>
  [
    /\d/.test(item.dimensoes ?? '') ? `${item.dimensoes}${item.altura ? '' : ' cm'}` : '',
    `Cor ${item.numero_cor}${item.corNome ? ` (${item.corNome})` : ''}`,
  ]
    .filter(Boolean)
    .join(' · ')
