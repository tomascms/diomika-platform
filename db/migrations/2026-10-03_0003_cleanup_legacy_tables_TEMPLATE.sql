-- APLICADO em produção a 2026-10-03 (36 tabelas renomeadas para legacy_*; reverter: ALTER TABLE legacy_x RENAME TO x).
-- ============================================================================
-- 0003: cleanup das 13 famílias de tabelas antigas — TEMPLATE, NÃO AUTOMÁTICO
-- ============================================================================
-- Só corre isto depois de:
--   1. 0001 + 0002 aplicados com sucesso;
--   2. a API (já no código novo, deste branch) a correr em produção há pelo
--      menos alguns dias sem erros relacionados com o catálogo;
--   3. teres comparado manualmente uma amostra de produtos na loja/backoffice
--      antes e depois, e confirmado que baterem certo.
--
-- Por segurança, isto RENOMEIA as tabelas antigas (prefixo `legacy_`) em vez
-- de as apagar — reversível. Passados uns meses, se nunca precisares de lá
-- voltar, podes fazer DROP TABLE legacy_* à mão.
-- ============================================================================

ALTER TABLE IF EXISTS modelos_almofadas RENAME TO legacy_modelos_almofadas;
ALTER TABLE IF EXISTS almofada RENAME TO legacy_almofada;
ALTER TABLE IF EXISTS modelo_almofada_cores RENAME TO legacy_modelo_almofada_cores;

ALTER TABLE IF EXISTS modelos_assentos RENAME TO legacy_modelos_assentos;
ALTER TABLE IF EXISTS assento RENAME TO legacy_assento;
ALTER TABLE IF EXISTS modelo_assento_cores RENAME TO legacy_modelo_assento_cores;

-- Só existe se a tua BD ainda tinha a tabela de cores partilhada legada:
ALTER TABLE IF EXISTS modelo_cores RENAME TO legacy_modelo_cores;

ALTER TABLE IF EXISTS modelos_guarda_chuvas RENAME TO legacy_modelos_guarda_chuvas;
ALTER TABLE IF EXISTS guarda_chuva RENAME TO legacy_guarda_chuva;
ALTER TABLE IF EXISTS modelo_guarda_chuva_cores RENAME TO legacy_modelo_guarda_chuva_cores;

ALTER TABLE IF EXISTS modelos_oculos RENAME TO legacy_modelos_oculos;
ALTER TABLE IF EXISTS oculo RENAME TO legacy_oculo;
ALTER TABLE IF EXISTS modelo_oculo_cores RENAME TO legacy_modelo_oculo_cores;

ALTER TABLE IF EXISTS modelos_toalhas_mesa RENAME TO legacy_modelos_toalhas_mesa;
ALTER TABLE IF EXISTS toalha_mesa RENAME TO legacy_toalha_mesa;
ALTER TABLE IF EXISTS modelo_toalha_mesa_cores RENAME TO legacy_modelo_toalha_mesa_cores;

ALTER TABLE IF EXISTS modelos_aventais RENAME TO legacy_modelos_aventais;
ALTER TABLE IF EXISTS avental RENAME TO legacy_avental;
ALTER TABLE IF EXISTS modelo_avental_cores RENAME TO legacy_modelo_avental_cores;

ALTER TABLE IF EXISTS modelos_luvas RENAME TO legacy_modelos_luvas;
ALTER TABLE IF EXISTS luva RENAME TO legacy_luva;
ALTER TABLE IF EXISTS modelo_luva_cores RENAME TO legacy_modelo_luva_cores;

ALTER TABLE IF EXISTS modelos_pegas RENAME TO legacy_modelos_pegas;
ALTER TABLE IF EXISTS pega RENAME TO legacy_pega;
ALTER TABLE IF EXISTS modelo_pega_cores RENAME TO legacy_modelo_pega_cores;

ALTER TABLE IF EXISTS modelos_panos_cozinha RENAME TO legacy_modelos_panos_cozinha;
ALTER TABLE IF EXISTS pano_cozinha RENAME TO legacy_pano_cozinha;
ALTER TABLE IF EXISTS modelo_pano_cozinha_cores RENAME TO legacy_modelo_pano_cozinha_cores;

ALTER TABLE IF EXISTS modelos_protetores_colchao RENAME TO legacy_modelos_protetores_colchao;
ALTER TABLE IF EXISTS protetor_colchao RENAME TO legacy_protetor_colchao;
ALTER TABLE IF EXISTS modelo_protetor_colchao_cores RENAME TO legacy_modelo_protetor_colchao_cores;

ALTER TABLE IF EXISTS modelos_passadeiras RENAME TO legacy_modelos_passadeiras;
ALTER TABLE IF EXISTS passadeira RENAME TO legacy_passadeira;
ALTER TABLE IF EXISTS modelo_passadeira_cores RENAME TO legacy_modelo_passadeira_cores;

ALTER TABLE IF EXISTS modelos_regionais RENAME TO legacy_modelos_regionais;
ALTER TABLE IF EXISTS regional RENAME TO legacy_regional;
ALTER TABLE IF EXISTS modelo_regional_cores RENAME TO legacy_modelo_regional_cores;
