/**
 * As denominações de fibras têxteis do Anexo I do Regulamento (UE) n.º 1007/2011 (auditoria LEGAL-12).
 *
 * Os artigos 5.º e 16.º só deixam usar, para dizer de que é feito um produto têxtil, estas denominações: «100 % poliéster»
 * é uma composição, «100 % veludo» não (o veludo é um tecido, não uma fibra: fica na descrição). A loja mostra a composição
 * tal como está na base de dados; o backoffice usa isto para avisar (não bloqueia) quem escreve uma que não está na lista
 * (backoffice-desktop/src/components/CompositionField.vue importa este ficheiro).
 *
 * As denominações são as do texto português do Jornal Oficial (L 272, de 18.10.2011), com as que os Regulamentos Delegados
 * (UE) n.º 286/2012 (bicomponente polipropileno/poliamida) e (UE) 2018/122 (poliacrilato) acrescentaram. JavaScript
 * simples, sem o alias «@» nem APIs do browser (o backoffice importa-o).
 */

/** O Anexo I, pela ordem das linhas (1 a 50), cada denominação como o texto a escreve. */
export const ANNEX_I_FIBRES = Object.freeze([
  'lã', // 1
  // 2: «precedido ou não da denominação «lã» ou «pêlo»»
  'alpaca',
  'lama',
  'camelo',
  'caxemira',
  'mohair',
  'angorá',
  'vicunha',
  'iaque',
  'guanaco',
  'caxegorá',
  'castor',
  'lontra',
  'pêlo', // 3: «pêlo ou crina com ou sem indicação da espécie animal»
  'crina',
  'seda', // 4
  'algodão',
  'sumaúma',
  'linho',
  'cânhamo',
  'juta',
  'abacá',
  'alfa',
  'coco',
  'giesta',
  'ramie',
  'sisal',
  'sunn',
  'henequen',
  'maguey', // 18
  'acetato', // 19
  'alginato',
  'cupro',
  'modal',
  'proteínas',
  'triacetato',
  'viscose',
  'acrílica',
  'clorofibra',
  'fluorofibra',
  'modacrílica',
  'poliamida ou nylon', // 30: as duas formas valem
  'poliamida',
  'nylon',
  'aramida',
  'poliimida',
  'liocel',
  'polilactida',
  'poliéster',
  'polietileno',
  'polipropileno',
  'policarbamida',
  'poliuretano',
  'vinilal',
  'trivinil',
  'elastodieno',
  'elastano',
  'fibra de vidro', // 44
  'elastomultiéster',
  'elastolefina',
  'melamina', // 47
  // 48: «denominação correspondente à matéria de que são compostas as fibras, por exemplo metal (metálica, metalizada),
  // amianto, papel, precedida ou não da palavra «fio» ou «fibra»»
  'metal',
  'metálica',
  'metalizada',
  'amianto',
  'papel',
  'polipropileno/poliamida bicomponente', // 49
  'poliacrilato', // 50
])

/** Sem acentos nem maiúsculas, com os espaços arrumados: «Poliéster » e «POLIESTER» são a mesma denominação. */
const fold = (text) =>
  String(text ?? '')
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()

const EXACT = new Set(ANNEX_I_FIBRES.map(fold))
const HAIR_ANIMALS = new Set([
  'alpaca',
  'lama',
  'camelo',
  'caxemira',
  'mohair',
  'angora',
  'vicunha',
  'iaque',
  'guanaco',
  'caxegora',
  'castor',
  'lontra',
])
const MATERIALS = new Set(['metal', 'metalica', 'metalizada', 'amianto', 'papel'])

/**
 * É uma denominação de fibra do Anexo I? Sem acentos nem maiúsculas.
 * @param {string} name
 */
export function isAnnexIFibre(name) {
  const text = fold(name)
  if (!text) return false
  if (EXACT.has(text)) return true
  // Linha 2: alpaca, lama… «precedido ou não de «lã» ou «pêlo»» («lã de alpaca»).
  const hair = /^(?:(?:la|pelo)(?: de)? )?(.+)$/.exec(text)
  if (hair && HAIR_ANIMALS.has(hair[1])) return true
  // Linha 3: pêlo ou crina, com ou sem a espécie («pêlo de bovino», «crina de cavalo»).
  if (/^(?:pelo|crina)(?: de [a-z ]+)?$/.test(text)) return true
  // Linha 48: a matéria, «precedida ou não da palavra «fio» ou «fibra»» («fio de metal», «fibra metálica»).
  const material = /^(?:(?:fio|fibra)(?: de)? )?(.+)$/.exec(text)
  return Boolean(material && MATERIALS.has(material[1]))
}

/**
 * Das denominações de uma composição, as que não são do Anexo I (para o aviso do backoffice).
 * @param {string[] | Record<string, unknown>} composition os nomes, ou o objecto `{ fibra: percentagem }` que a base de dados guarda
 * @returns {string[]} como foram escritas (sem espaços nas pontas), sem repetir
 */
export function nonAnnexIFibres(composition) {
  const names = Array.isArray(composition) ? composition : Object.keys(composition ?? {})
  const unknown = names
    .map((name) => String(name ?? '').trim())
    .filter((name) => name && !isAnnexIFibre(name))
  return [...new Set(unknown)]
}
