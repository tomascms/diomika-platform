-- P0: EAN único por tabela de produto (parcial — ignora NULL/vazio).
-- Unicidade entre famílias: validação na API (admin_crud._assert_ean_globally_unique).

CREATE UNIQUE INDEX IF NOT EXISTS uq_almofada_ean
  ON almofada (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_assento_ean
  ON assento (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_guarda_chuva_ean
  ON guarda_chuva (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_oculo_ean
  ON oculo (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_toalha_mesa_ean
  ON toalha_mesa (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_avental_ean
  ON avental (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_luva_ean
  ON luva (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_pega_ean
  ON pega (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_pano_cozinha_ean
  ON pano_cozinha (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_regional_ean
  ON regional (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
