-- ============================================================================
-- Ciclo do orçamento no backoffice (auditoria RP-06, LEGAL-09), tarefa 2.7
-- ============================================================================
-- Colunas novas anuláveis e um estado novo («Proposta enviada»). Nada se apaga nem se reescreve. Idempotente.
-- ORDEM: aplicar ANTES do backoffice novo e da API que traz PATCH /admin/crud/pedidos_orcamento/{id}/gestao.
-- Depois de 2026-11-02_new_columns.sql (vendido_em) e de 2026-11-02_database_hardening.sql (a restrição de estados).

ALTER TABLE public.pedidos_orcamento ADD COLUMN IF NOT EXISTS valor_proposta numeric(12, 2);
ALTER TABLE public.pedidos_orcamento ADD COLUMN IF NOT EXISTS nota_interna text;

ALTER TABLE public.pedidos_orcamento DROP CONSTRAINT IF EXISTS ck_pedidos_orcamento_status;
ALTER TABLE public.pedidos_orcamento ADD CONSTRAINT ck_pedidos_orcamento_status
  CHECK (status IN ('Nova', 'Email pendente', 'Em tratamento', 'Proposta enviada', 'Vendido', 'Cancelado', 'Arquivado', 'Rejeitado')) NOT VALID;

DO $do$
BEGIN
  ALTER TABLE public.pedidos_orcamento VALIDATE CONSTRAINT ck_pedidos_orcamento_status;
EXCEPTION WHEN check_violation THEN
  RAISE WARNING 'pedidos_orcamento tem estados fora da lista: a restrição vale só para linhas novas';
END
$do$;
