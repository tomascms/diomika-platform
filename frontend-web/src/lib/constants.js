export const MIN_ORCAMENTO_MSG =
  'Mínimo de encomenda: 500€ + IVA. O site não apresenta preços — envie o pedido para receber orçamento.'

export const COMPANY = {
  name: 'Diomika',
  phoneDisplay: '935 745 663',
  phoneTel: '+351935745663',
  whatsappE164: '351935745663',
  address: 'Rua da Quintã, n.º 89',
  postal: '4805-116 Caldas das Taipas',
  nif: '508 651 557',
}

/** Link WhatsApp com texto opcional pré-preenchido. */
export function whatsappUrl(text = '') {
  const base = `https://wa.me/${COMPANY.whatsappE164}`
  const t = String(text || '').trim()
  return t ? `${base}?text=${encodeURIComponent(t)}` : base
}

export const QUOTE_FORM_DRAFT_KEY = 'diomika_quote_form_draft'