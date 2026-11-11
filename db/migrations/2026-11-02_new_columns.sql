-- ============================================================================
-- Colunas novas: descrição da categoria, origem do pedido, data de venda
-- (auditoria RP-08, RP-10, LEGAL-09)
-- ============================================================================
-- Todas anuláveis ou com valor por omissão; nada se apaga nem se reescreve. Idempotente.
--
-- ORDEM: aplicar ANTES da API nova. A API selecciona `categories.descricao` nas listas públicas de
-- categorias e grava `origem` quando o formulário a traz; sem a coluna o PostgREST responde 400.
-- ============================================================================

-- RP-08: texto de categoria (SEO e contexto de compra). Vazio = a loja não mostra nada.
ALTER TABLE public.categories ADD COLUMN IF NOT EXISTS descricao text NOT NULL DEFAULT '';

-- RP-10: de onde veio o pedido (página de entrada, domínio de referência, UTM, último produto visto).
-- jsonb sem dados pessoais nem cookies: a API só deixa passar as chaves listadas em core/origem.py.
ALTER TABLE public.pedidos_orcamento ADD COLUMN IF NOT EXISTS origem jsonb;
ALTER TABLE public.contact_messages ADD COLUMN IF NOT EXISTS origem jsonb;

-- LEGAL-09: a retenção por idade dos pedidos poupa os que acabaram em venda. A tarefa 2.7 passa a
-- preencher esta data no backoffice; até lá fica sempre NULL e a retenção por idade fica desligada.
ALTER TABLE public.pedidos_orcamento ADD COLUMN IF NOT EXISTS vendido_em timestamptz;
