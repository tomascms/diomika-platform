// Encomenda mínima (LEGAL-11): 500 € sem IVA e, para particulares, 615 € com IVA a 23 % (a taxa
// confirma-a o contabilista: ficha do cliente, Parte D, item 11). Espaços não separáveis: «500 €» e «23 %»
// não se partem ao mudar de linha.
export const MIN_ORDER = '500\u00a0€ + IVA (615\u00a0€ com IVA a 23\u00a0%)'

// LEGAL-11: a oferta em linha é para revendedores; a um particular, a proposta traz sempre o preço final.
export const PRICE_NOTE =
  'A oferta em linha dirige-se sobretudo a revendedores; a particulares, a proposta indica sempre o preço total com IVA e portes.'

// Quem compra, numa linha, no início e em «Sobre nós» (RP-15). Os preços continuam «sob pedido».
export const SELLS_TO_LINE = `Vendemos a lojas, hotelaria e particulares — pedido mínimo ${MIN_ORDER}.`

export const MIN_ORCAMENTO_MSG = `Mínimo de encomenda: ${MIN_ORDER}. O preço vem na proposta.`

/** O endereço canónico da loja: o das páginas para os motores de busca e o que o WhatsApp leva ao modelo. */
export const SITE_ORIGIN = 'https://www.diomika.com'

// Identificação permanente do prestador: DL 7/2004, art. 10.º, e CSC, art. 171.º.
export const COMPANY = {
  name: 'Diomika',
  legalName: 'DIOMIKA INTERNACIONAL, UNIPESSOAL, LDA',
  registry: 'Conservatória do Registo Comercial',
  phoneDisplay: '935 745 663',
  phoneTel: '+351935745663',
  whatsappE164: '351935745663',
  address: 'Rua da Quintã, n.º 89',
  // Por confirmar na certidão permanente (4805-116 no site, 4805-149 no eInforma): ficha do
  // cliente, Parte D, item 1. Ao corrigir, mudar também o JSON-LD de index.html.
  postal: '4805-116 Caldas das Taipas',
  municipality: 'Guimarães',
  // NIPC, o NIF das sociedades e também o número de matrícula. Mostra-se como «NIPC».
  nif: '508 651 557',
  // Vazios até o cliente os dar (ficha do cliente, Parte D, itens 1 e 2): só se mostram se tiverem
  // valor. Ao preencher, ex. '5 000 €', acrescentar o email também ao JSON-LD de index.html.
  shareCapital: '',
  email: '',
}

/** Livro de Reclamações Eletrónico (DL 156/2005, art. 5.º-B). */
export const COMPLAINTS_BOOK_URL = 'https://www.livroreclamacoes.pt'

/** Ligação ao mapa da sede (RP-09). Só uma ligação: não se incorpora um mapa de terceiros. */
export const MAP_URL = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
  `${COMPANY.address}, ${COMPANY.postal}, ${COMPANY.municipality}`,
)}`

/**
 * Entidade de resolução alternativa de litígios de consumo (Lei 144/2015, art. 18.º). O nome é o do
 * Regulamento Harmonizado do TRIAVE, de março de 2026.
 */
export const ADR_ENTITY = {
  name: 'TRIAVE – Centro de Arbitragem de Conflitos de Consumo do Ave, Tâmega e Sousa',
  site: 'www.triave.pt',
}

// Custo da chamada a indicar junto do número (DL 59/2021, art. 4.º): 2… é rede fixa, 9… é móvel.
const CALL_COST_NOTE = {
  2: 'Chamada para a rede fixa nacional',
  9: 'Chamada para a rede móvel nacional',
}

/** Nota do custo da chamada de um número («935 745 663» ou «+351935745663»), ou '' se não for 2… nem 9…. */
export function callCostNote(phone) {
  return CALL_COST_NOTE[String(phone).replace(/\D/g, '').slice(-9)[0]] ?? ''
}

/** Link WhatsApp com texto opcional pré-preenchido. */
export function whatsappUrl(text = '') {
  const base = `https://wa.me/${COMPANY.whatsappE164}`
  const t = String(text || '').trim()
  return t ? `${base}?text=${encodeURIComponent(t)}` : base
}

export const QUOTE_FORM_DRAFT_KEY = 'diomika_quote_form_draft'
