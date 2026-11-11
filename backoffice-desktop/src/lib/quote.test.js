import test from 'node:test'
import assert from 'node:assert/strict'
import { QUOTE_STATUSES, REPLY_TEMPLATES, lineText, mailtoUrl, managementChanges, origemLines, statusLabel } from './quote.js'

test('estados: o ciclo completo e as palavras do guia', () => {
  assert.deepEqual(
    QUOTE_STATUSES.map((s) => s.value),
    ['Nova', 'Em tratamento', 'Proposta enviada', 'Vendido', 'Cancelado', 'Arquivado'],
  )
  assert.equal(statusLabel('Vendido'), 'Ganho (vendido)')
  assert.equal(statusLabel(undefined), 'Nova')
})

test('linhas: nome, medida e cor; sem nome cai para o EAN', () => {
  assert.equal(
    lineText({ ean: '4006381333931', modelo: 'Agate', dimensoes: '45x45', cor_nome: 'Azul', numero_cor: 1, quantidade: 12 }),
    'Agate · 45x45 · Azul (cor 1) · qtd 12',
  )
  assert.equal(
    lineText({ ean: '4006381333931', modelo: '?', dimensoes: '?', numero_cor: 2, quantidade: 5, altura: '32mm' }),
    'EAN 4006381333931 · 32mm · cor 2 · qtd 5',
  )
})

test('origem: só o que existe, por ordem; pedidos antigos não mostram nada', () => {
  assert.deepEqual(origemLines({ produto: 'agate', entrada: '/carrinho', referrer: 'www.google.com' }), [
    'Entrou por: /carrinho',
    'Veio de: www.google.com',
    'Último modelo visto: agate',
  ])
  assert.deepEqual(origemLines(null), [])
})

test('gestão: só vai o que mudou; valor com vírgula e vazio limpam', () => {
  const rec = { status: 'Nova', valor_proposta: null, nota_interna: null }
  assert.deepEqual(managementChanges(rec, { status: 'Nova', valor_proposta: '', nota_interna: '' }), {})
  assert.deepEqual(managementChanges(rec, { status: 'Vendido', valor_proposta: '1234,5', nota_interna: 'ligar' }), {
    status: 'Vendido',
    valor_proposta: '1234,5',
    nota_interna: 'ligar',
  })
  assert.deepEqual(
    managementChanges({ ...rec, valor_proposta: 80 }, { status: 'Nova', valor_proposta: '', nota_interna: '' }),
    { valor_proposta: '' },
  )
})

test('modelos de resposta: a proposta pede «Aceito»; a confirmação é em suporte duradouro; nada de email pessoal', () => {
  const rec = { id: '3f2a9c1b-0000-4000-8000-000000000000', nome: 'Ana', email: 'ana@example.com' }
  const [proposta, confirmacao] = REPLY_TEMPLATES.map((t) => t.build(rec))
  assert.match(proposta.body, /«Aceito»/)
  assert.match(proposta.body, /14 dias/)
  assert.match(proposta.body, /livroreclamacoes\.pt/)
  assert.match(proposta.body, /condicoes-de-venda/)
  assert.match(proposta.subject, /3f2a9c1b/)
  assert.match(confirmacao.body, /suporte duradouro/)
  for (const m of [proposta, confirmacao]) assert.doesNotMatch(m.subject + m.body, /gmail|@diomika/)
})

test('mailto: codifica o assunto e o corpo', () => {
  const url = mailtoUrl('ana@example.com', { subject: 'A & B', body: 'linha 1\nlinha 2' })
  assert.equal(url, 'mailto:ana%40example.com?subject=A%20%26%20B&body=linha%201%0Alinha%202')
})
