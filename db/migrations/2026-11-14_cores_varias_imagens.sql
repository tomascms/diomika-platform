-- ============================================================================
-- Cores com mais do que uma imagem
-- ============================================================================
-- `imagens`: todas as imagens de cada cor, por ordem. `imagem` continua a ser a primeira (a principal), por isso
-- quem já lê `imagem` (loja, verificação de «publicar», imagens em falta) não muda.
-- As cores que já existem ficam com a imagem que tinham em `imagens`.
--
-- Idempotente. Não apaga nem reescreve dados que já lá estão.
-- ============================================================================

ALTER TABLE product_model_colors ADD COLUMN IF NOT EXISTS imagens text[] NOT NULL DEFAULT '{}';

UPDATE product_model_colors
   SET imagens = ARRAY[imagem]
 WHERE imagem <> '' AND imagens = '{}';

COMMENT ON COLUMN product_model_colors.imagens IS 'Todas as imagens da cor, por ordem; a primeira é a principal (igual a `imagem`).';
