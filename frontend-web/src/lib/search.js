/**
 * Que categorias correspondem ao que se escreveu numa pesquisa (auditoria FE-06, RP-07).
 *
 * Os modelos procura-os a API (`GET /catalogo/search`, backend-api/core/catalog_search.py). Isto serve só a lista de
 * categorias que a loja já tem em memória: sugerir «Almofada» a quem escreveu «almofda». Segue as mesmas regras da API,
 * por isso uma e outra concordam: sem acentos nem maiúsculas, sem o «s» final, todas as palavras (as vazias, como «de»,
 * não contam) e uma gralha perdoada em palavras com 5 ou mais letras. JavaScript simples, sem o alias «@».
 */

// As mesmas palavras vazias de backend-api/core/catalog_search.py.
const STOPWORDS = new Set(['a', 'o', 'e', 'de', 'do', 'da', 'dos', 'das', 'em', 'para', 'com'])

const fold = (text) =>
  String(text ?? '')
    .toLowerCase()
    .replaceAll('×', 'x')
    .normalize('NFD')
    .replace(/\p{M}/gu, '')

/** Tira o «s» final («almofadas» → «almofada»); não mexe em números nem em palavras curtas. */
const stem = (word) =>
  word.length > 3 && word.endsWith('s') && !/\d/.test(word) ? word.slice(0, -1) : word

/** As palavras de um texto, comparáveis: sem acentos, maiúsculas nem «s» final; «45 x 45» e «45×45» são «45x45». */
export function searchWords(text) {
  const folded = fold(text)
    .replace(/(?<=\d)\s*x\s*(?=\d)/g, 'x')
    .replace(/(?<=\d)\s+(?=(?:mm|cm|m)\b)/g, '')
  return (folded.match(/[a-z0-9]+/g) ?? []).map(stem)
}

/** A distância entre as palavras (inserir, apagar, trocar uma letra, trocar duas seguidas) é no máximo `limit`? */
function within(a, b, limit) {
  if (Math.abs(a.length - b.length) > limit) return false
  let beforePrevious = null
  let previous = Array.from({ length: b.length + 1 }, (_, j) => j)
  for (let i = 1; i <= a.length; i++) {
    const current = [i, ...Array(b.length).fill(0)]
    for (let j = 1; j <= b.length; j++) {
      current[j] = Math.min(
        previous[j] + 1,
        current[j - 1] + 1,
        previous[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      )
      if (beforePrevious && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
        current[j] = Math.min(current[j], beforePrevious[j - 2] + 1)
      }
    }
    beforePrevious = previous
    previous = current
  }
  return previous[b.length] <= limit
}

/** A palavra da pesquisa corresponde à do nome: igual, parte dela (3 ou mais letras) ou com uma gralha (5 ou mais, só letras). */
function matches(word, candidate) {
  if (word === candidate) return true
  if (/\d/.test(word)) return false
  if (word.length >= 3 && candidate.includes(word)) return true
  return (
    word.length >= 5 && /^[a-z]+$/.test(word) && within(word, candidate, word.length < 8 ? 1 : 2)
  )
}

/**
 * As categorias cujo nome tem todas as palavras da pesquisa, pela ordem em que vêm.
 * @param {string} term o que se escreveu
 * @param {{ nome?: string, slug?: string }[]} categories a lista da loja (já sem as vazias)
 */
export function matchCategories(term, categories) {
  const all = searchWords(term)
  const words = all.filter((word) => !STOPWORDS.has(word))
  const wanted = words.length ? words : all
  if (!wanted.length) return []
  return (categories ?? []).filter((category) => {
    const names = searchWords(`${category.nome ?? ''} ${category.slug ?? ''}`)
    return wanted.every((word) => names.some((name) => matches(word, name)))
  })
}
