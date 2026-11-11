-- ============================================================================
-- Modelos sem descrição: o texto «Sem descrição» dos dados antigos passa a vazio
-- (auditoria BD-01, RP-02, FE-03)
-- ============================================================================
-- 28 modelos têm o texto literal «Sem descrição» em product_models.descricao. A loja já o trata como
-- vazio (frontend-web/src/lib/describe.js) e escreve a descrição a partir das especificações; isto
-- limpa a base de dados para o backoffice, a API e as pesquisas deixarem de o ver. A coluna é
-- `text DEFAULT ''`, por isso «vazio» é '' e não NULL (os modelos Pydantic esperam texto).
--
-- Idempotente: uma segunda execução não encontra nada para alterar. Só mexe na coluna `descricao`,
-- e só onde o texto começa por «Sem descri…» (a mesma regra da loja).
-- Não está aplicada em lado nenhum; aplicar é do coordenador (escrita em produção).
-- ============================================================================

UPDATE product_models
SET descricao = ''
WHERE descricao ~* '^\s*sem descri';
