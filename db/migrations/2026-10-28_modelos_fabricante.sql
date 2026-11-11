-- ============================================================================
-- Fabricante ou importador e avisos de segurança de cada modelo
-- (auditoria LEGAL-12)
-- ============================================================================
-- Reg. (UE) 2023/988 (segurança geral dos produtos), art. 19.º: o artigo, ou a sua oferta em linha, tem de dizer quem o
-- fabrica ou importa (nome, morada, contacto electrónico) e levar os avisos de segurança. Quatro colunas novas em
-- `product_models`, todas anuláveis e sem valor por omissão: os modelos que já existem ficam com NULL e a loja só mostra
-- o que tiver valor. Quem as preenche é o cliente, no backoffice (ficha do cliente, Parte D, item 10).
--
-- Ordem de publicação: aplicar isto antes ou depois da API nova, tanto faz: a API só envia estas colunas quando o
-- formulário as preenche (um modelo que nunca as teve grava-se como antes), e a loja lê `*`.
--
-- Idempotente. Não apaga nem reescreve dados.
-- ============================================================================

ALTER TABLE product_models ADD COLUMN IF NOT EXISTS fabricante_nome text;
ALTER TABLE product_models ADD COLUMN IF NOT EXISTS fabricante_morada text;
ALTER TABLE product_models ADD COLUMN IF NOT EXISTS fabricante_email text;
ALTER TABLE product_models ADD COLUMN IF NOT EXISTS avisos text;

COMMENT ON COLUMN product_models.fabricante_nome IS 'Fabricante ou importador do artigo: nome (Reg. UE 2023/988, art. 19.º).';
COMMENT ON COLUMN product_models.fabricante_morada IS 'Fabricante ou importador do artigo: morada postal.';
COMMENT ON COLUMN product_models.fabricante_email IS 'Fabricante ou importador do artigo: contacto electrónico.';
COMMENT ON COLUMN product_models.avisos IS 'Avisos de segurança do artigo (texto livre; uma linha por aviso).';
