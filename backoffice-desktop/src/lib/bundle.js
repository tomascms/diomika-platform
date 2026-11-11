/**
 * Gravação de um modelo com as suas cores e EAN num só pedido (API-08): o corpo de POST /admin/crud/{modelos}/bundle.
 * Funções puras; os painéis de cores e de produtos só lhes dão as linhas do ecrã (testes em bundle.test.js).
 * Uma falha em qualquer linha pára tudo antes de se enviar: a API é atómica, o ecrã também.
 */

/** Falta uma cor ou um EAN para publicar: o modelo pode na mesma ser guardado como rascunho (`missingRows: true`). */
function missingRows(text) {
  return Object.assign(new Error(text), { missingRows: true })
}

/** Linhas de cor → corpo da API. `newId` dá o id às linhas novas. Lança Error com texto para mostrar. */
export function colorItems(rows, { visible = false, requireRows = false, newId }) {
  const filled = rows.filter((row) => String(row.numero || '').trim())
  if (requireRows && !filled.length) {
    throw missingRows('Adicione pelo menos uma cor (número + imagem).')
  }
  return filled.map((row) => {
    if (!row.imagem) throw new Error(`Cor nº ${String(row.numero).trim()}: escolha uma imagem.`)
    return {
      id: row.id || newId(),
      numero: parseInt(String(row.numero).trim(), 10),
      nome: (row.nome || '').trim(),
      imagem: row.imagem,
      visibilidade: visible,
    }
  })
}

/** Linhas de produto → corpo da API. `extraField` é o atributo da variante (dimensões, altura…) ou null. */
export function variantItems(rows, { extraField = null, visible = false, requireRows = false, newId }) {
  const filled = rows.filter((row) => String(row.ean || '').trim())
  if (requireRows && !filled.length) {
    throw missingRows('Adicione pelo menos um produto (EAN) antes de publicar na loja.')
  }
  return filled.map((row) => {
    const ean = String(row.ean).trim()
    if (!/^\d{13}$/.test(ean)) throw new Error(`EAN «${row.ean}» inválido — tem de ter 13 dígitos.`)
    if (extraField?.required && !String(row.extra || '').trim()) {
      throw new Error(`EAN ${row.ean}: indique ${extraField.label.toLowerCase()}.`)
    }
    return {
      id: row.id || newId(),
      ean,
      attributes: extraField ? { [extraField.name]: row.extra } : {},
      visibilidade: visible,
    }
  })
}

/** O corpo completo. `deleteColors`/`deleteVariants`: os ids que estavam gravados e o utilizador tirou da lista. */
export function bundleBody({ model, colors, variants, deleteColors = [], deleteVariants = [] }) {
  return {
    model,
    colors,
    variants,
    delete_colors: deleteColors,
    delete_variants: deleteVariants,
  }
}
