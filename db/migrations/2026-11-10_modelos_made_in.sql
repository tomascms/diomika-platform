-- ============================================================================
-- «Made in»: país de fabrico de cada modelo (aparece no fim da etiqueta Brother)
-- ============================================================================
-- Uma coluna nova e anulável em `product_models`. Os modelos que já existem ficam com NULL e a etiqueta não mostra
-- a linha «Made in». Quem a preenche é o cliente, no formulário do modelo do backoffice.
--
-- Idempotente. Não apaga nem reescreve dados.
-- ============================================================================

ALTER TABLE product_models ADD COLUMN IF NOT EXISTS made_in text;

COMMENT ON COLUMN product_models.made_in IS 'País de fabrico do modelo (texto livre, ex: Portugal). Aparece na etiqueta como «Made in …».';
