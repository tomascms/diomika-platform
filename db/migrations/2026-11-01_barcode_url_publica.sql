-- ============================================================================
-- Códigos de barras: o URL público em vez do assinado, que já expirou
-- (auditoria SEO-07, FE-10)
-- ============================================================================
-- Os códigos de barras gerados com o bucket privado ficaram na BD com o URL assinado do Storage
-- (`/storage/v1/object/sign/…?token=…`), que expira: hoje o Storage responde 400 («InvalidJWT») e a imagem
-- aparece partida. O mesmo caminho em `/object/public/…` abre. São imagens de EAN, sem nada de privado.
--
-- Troca `/object/sign/` por `/object/public/` e tira o `?token=…`. A API passa a gravar o URL público
-- (utils/barcode_gen.py) e a loja nunca confia no URL gravado (resolve-o outra vez antes de o mostrar).
--
-- Idempotente: uma segunda execução já não encontra nenhum URL assinado. Só mexe em `barcode_url`.
-- Não está aplicada em lado nenhum; aplicar é do coordenador (escrita em produção).
-- ============================================================================

UPDATE product_variants
SET barcode_url = replace(
  split_part(barcode_url, '?', 1),
  '/storage/v1/object/sign/',
  '/storage/v1/object/public/'
)
WHERE barcode_url LIKE '%/storage/v1/object/sign/%';
