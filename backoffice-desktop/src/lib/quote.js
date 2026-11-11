/**
 * Orçamentos no backoffice (RP-06, RP-10, LEGAL-01): estados, linhas legíveis, origem e modelos de resposta.
 * Funções puras: os ecrãs só as chamam (testes em quote.test.js).
 */

// Os valores são os da restrição da BD e da API (backend-api/routes/admin_crud.py QUOTE_STATUSES).
export const QUOTE_STATUSES = [
  { value: 'Nova', label: 'Nova' },
  { value: 'Em tratamento', label: 'Em análise' },
  { value: 'Proposta enviada', label: 'Proposta enviada' },
  { value: 'Vendido', label: 'Ganho (vendido)' },
  { value: 'Cancelado', label: 'Perdido' },
  { value: 'Arquivado', label: 'Arquivado' },
]

export function statusLabel(status) {
  return QUOTE_STATUSES.find((s) => s.value === status)?.label || status || 'Nova'
}

/** «Agate · 45×45 · Azul (cor 1) · qtd 12». Sem nome (modelo antigo ou apagado) cai para o EAN. */
export function lineText(line) {
  const named = line.modelo && line.modelo !== '?'
  const parts = [
    named ? line.modelo : `EAN ${line.ean}`,
    line.dimensoes && line.dimensoes !== '?' ? line.dimensoes : null,
    line.altura || null,
    line.cor_nome ? `${line.cor_nome} (cor ${line.numero_cor})` : `cor ${line.numero_cor}`,
    `qtd ${line.quantidade}`,
  ].filter(Boolean)
  return parts.join(' · ')
}

const ORIGEM_LABELS = [
  ['entrada', 'Entrou por'],
  ['referrer', 'Veio de'],
  ['utm_source', 'Fonte'],
  ['utm_medium', 'Meio'],
  ['utm_campaign', 'Campanha'],
  ['produto', 'Último modelo visto'],
]

/** Linhas «Entrou por: /carrinho». Vazio quando o pedido não traz origem (pedidos antigos). */
export function origemLines(origem) {
  if (!origem || typeof origem !== 'object') return []
  return ORIGEM_LABELS.filter(([key]) => origem[key]).map(([key, label]) => `${label}: ${origem[key]}`)
}

/** Só o que mudou, no formato do PATCH /gestao. `valor` aceita vírgula decimal; vazio limpa. */
export function managementChanges(record, form) {
  const out = {}
  if (form.status && form.status !== (record.status || 'Nova')) out.status = form.status
  const before = record.valor_proposta == null ? '' : String(record.valor_proposta)
  if (String(form.valor_proposta ?? '').trim() !== before) out.valor_proposta = String(form.valor_proposta ?? '').trim()
  if ((form.nota_interna || '').trim() !== (record.nota_interna || '').trim()) out.nota_interna = form.nota_interna || ''
  return out
}

const SITE = 'https://www.diomika.com'

const refOf = (record) => String(record.id || '').slice(0, 8)

function greeting(record) {
  return record.nome ? `Bom dia, ${record.nome},` : 'Bom dia,'
}

const SIGNATURE = [
  'Com os melhores cumprimentos,',
  'DIOMIKA INTERNACIONAL, UNIPESSOAL, LDA',
  'NIF 508 651 557 · Rua da Quintã, n.º 89, 4805-116 Caldas das Taipas',
].join('\n')

/**
 * Modelos de resposta (LEGAL-01). Os [parênteses rectos] são o que quem responde tem de preencher; nada se
 * inventa. A proposta leva sempre as condições gerais (CGV) e, a particulares, a informação do DL 24/2014.
 */
export const REPLY_TEMPLATES = [
  {
    id: 'proposta-particular',
    label: 'Proposta a particular',
    build(record) {
      return {
        subject: `Proposta Diomika — pedido n.º ${refOf(record)}`,
        body: [
          greeting(record),
          '',
          `Obrigado pelo seu pedido n.º ${refOf(record)}. Segue a nossa proposta:`,
          '',
          '[Artigos, quantidades, cores e medidas]',
          '',
          'Preço total, com IVA incluído: [valor] €',
          'Portes de envio: [valor] € (ou: [modo de cálculo])',
          'Pagamento: [modalidades]',
          'Entrega: [morada], prazo [prazo de entrega]',
          'Esta proposta é válida até [data].',
          '',
          'Informação que a lei nos manda dar antes de aceitar:',
          '- Tem direito a resolver o contrato, sem indicar motivo, no prazo de 14 dias a contar da recepção dos bens (livre resolução). O formulário-modelo está nas condições gerais de venda. Não se aplica a produtos feitos por medida ou personalizados.',
          '- Os bens têm garantia legal de 3 anos.',
          '- Reclamações: livro de reclamações electrónico em https://www.livroreclamacoes.pt; respondemos no prazo de 15 dias úteis.',
          '- [Entidade de resolução alternativa de litígios de consumo: indicar a que a empresa escolher]',
          `- Condições gerais de venda: ${SITE}/condicoes-de-venda (seguem com esta proposta e aplicam-se a esta venda).`,
          '',
          'Para aceitar, responda a este email com a palavra «Aceito». Uma aceitação só por telefone não fecha o contrato.',
          '',
          SIGNATURE,
        ].join('\n'),
      }
    },
  },
  {
    id: 'confirmacao-encomenda',
    label: 'Confirmação de encomenda',
    build(record) {
      return {
        subject: `Confirmação da encomenda — pedido n.º ${refOf(record)}`,
        body: [
          greeting(record),
          '',
          `Confirmamos a sua encomenda, referente ao pedido n.º ${refOf(record)}, aceite por escrito em [data da aceitação].`,
          '',
          '[Artigos, quantidades, cores e medidas]',
          'Preço total, com IVA incluído: [valor] € · Portes: [valor] €',
          'Entrega: [morada], prazo [prazo de entrega]',
          '',
          'Esta mensagem é a confirmação do contrato num suporte duradouro e repete as informações da proposta aceite, incluindo o direito de livre resolução de 14 dias e a garantia legal de 3 anos.',
          `Condições gerais de venda: ${SITE}/condicoes-de-venda`,
          '',
          SIGNATURE,
        ].join('\n'),
      }
    },
  },
]

/** Ligação `mailto:` com o modelo; quem tem o email configurado vê a mensagem já escrita. */
export function mailtoUrl(email, { subject, body }) {
  return `mailto:${encodeURIComponent(email || '')}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}
