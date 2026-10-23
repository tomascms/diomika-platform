-- ============================================================================
-- 0002: migração de dados — 13 famílias de tabelas antigas → 3 tabelas novas
-- ============================================================================
-- ⚠️ IMPORTANTE — LER ANTES DE CORRER:
-- Este script foi escrito a partir do código (schemas.py, migrations antigas)
-- e NÃO foi validado contra a tua base de dados Supabase real — esta sessão
-- não teve acesso de leitura à BD de produção. O código e a BD já tinham
-- divergido antes deste refactor (ex.: almofada+assento partilhavam uma
-- tabela `modelo_cores`, enquanto o código assumia `modelo_almofada_cores` /
-- `modelo_assento_cores` próprias) — por isso este script tenta as duas
-- hipóteses para a tabela de cores de cada família (table dedicada primeiro,
-- `modelo_cores` partilhada como fallback) e SALTA em silêncio (via
-- to_regclass IS NOT NULL) qualquer tabela que não exista — mas confirma os
-- números no PASSO 3 antes de confiares no resultado.
--
-- Mantém os IDs originais (id do modelo/produto/cor não muda) — assim
-- product_variants.id_modelo e product_model_colors.id_modelo continuam a
-- apontar para o mesmo registo migrado, sem precisar de uma tabela de
-- remapeamento.
--
-- NÃO apaga nem altera nenhuma tabela antiga. Corre 0001 primeiro.
--
-- PASSO 1 — corre tudo dentro de uma transacção, para poderes verificar antes
-- de confirmar:
--
--   BEGIN;
--   \i 0002_migrate_catalog_data.sql
--   -- ...corre as queries de verificação do PASSO 3 aqui...
--   -- Se os números baterem certo:
--   COMMIT;
--   -- Se algo parecer errado:
--   ROLLBACK;
-- ============================================================================


-- === Almofadas ===
DO $$
BEGIN
  IF to_regclass('public.modelos_almofadas') IS NOT NULL THEN
    INSERT INTO product_models (id, id_categoria, tipo_catalogo, nome, slug, descricao, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_categoria, 'almofada', nome, COALESCE(slug, ''), COALESCE(descricao, ''),
           jsonb_build_object('tipo', tipo, 'composicao', COALESCE(composicao, '{}'::jsonb), 'dimensoes', COALESCE(to_jsonb(dimensoes), '[]'::jsonb)),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), COALESCE(updated_at, now())
    FROM modelos_almofadas
    ON CONFLICT (id) DO NOTHING;
  END IF;

  IF to_regclass('public.almofada') IS NOT NULL THEN
    INSERT INTO product_variants (id, id_modelo, tipo_catalogo, ean, barcode_url, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_modelo, 'almofada', ean, barcode_url,
           jsonb_build_object('dimensoes', dimensoes),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), COALESCE(updated_at, now())
    FROM almofada
    ON CONFLICT (id) DO NOTHING;
  END IF;

  IF to_regclass('public.modelo_almofada_cores') IS NOT NULL THEN
    INSERT INTO product_model_colors (id, id_modelo, numero, nome, imagem, visibilidade, created_at)
    SELECT id, id_modelo, numero, COALESCE(nome, ''), COALESCE(imagem, ''), COALESCE(visibilidade, false), COALESCE(created_at, now())
    FROM modelo_almofada_cores
    ON CONFLICT (id_modelo, numero) DO NOTHING;
  ELSIF to_regclass('public.modelo_cores') IS NOT NULL THEN
    -- Fallback: tabela de cores partilhada legada (almofada + assento), com coluna tipo_catalogo.
    INSERT INTO product_model_colors (id, id_modelo, numero, nome, imagem, visibilidade, created_at)
    SELECT id, id_modelo, numero, COALESCE(nome, ''), COALESCE(imagem, ''), COALESCE(visibilidade, false), COALESCE(created_at, now())
    FROM modelo_cores
    WHERE tipo_catalogo = 'almofada' OR id_modelo IN (SELECT id FROM modelos_almofadas)
    ON CONFLICT (id_modelo, numero) DO NOTHING;
  END IF;
END $$;


-- === Assentos ===
DO $$
BEGIN
  IF to_regclass('public.modelos_assentos') IS NOT NULL THEN
    INSERT INTO product_models (id, id_categoria, tipo_catalogo, nome, slug, descricao, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_categoria, 'assento', nome, COALESCE(slug, ''), COALESCE(descricao, ''),
           jsonb_build_object('material_forro', material_forro, 'material_enchimento', material_enchimento, 'alturas', COALESCE(alturas, '[]'::jsonb)),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), COALESCE(updated_at, now())
    FROM modelos_assentos
    ON CONFLICT (id) DO NOTHING;
  END IF;

  IF to_regclass('public.assento') IS NOT NULL THEN
    INSERT INTO product_variants (id, id_modelo, tipo_catalogo, ean, barcode_url, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_modelo, 'assento', ean, barcode_url,
           jsonb_build_object('altura', altura),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), COALESCE(updated_at, now())
    FROM assento
    ON CONFLICT (id) DO NOTHING;
  END IF;

  IF to_regclass('public.modelo_assento_cores') IS NOT NULL THEN
    INSERT INTO product_model_colors (id, id_modelo, numero, nome, imagem, visibilidade, created_at)
    SELECT id, id_modelo, numero, COALESCE(nome, ''), COALESCE(imagem, ''), COALESCE(visibilidade, false), COALESCE(created_at, now())
    FROM modelo_assento_cores
    ON CONFLICT (id_modelo, numero) DO NOTHING;
  ELSIF to_regclass('public.modelo_cores') IS NOT NULL THEN
    INSERT INTO product_model_colors (id, id_modelo, numero, nome, imagem, visibilidade, created_at)
    SELECT id, id_modelo, numero, COALESCE(nome, ''), COALESCE(imagem, ''), COALESCE(visibilidade, false), COALESCE(created_at, now())
    FROM modelo_cores
    WHERE tipo_catalogo = 'assento' OR id_modelo IN (SELECT id FROM modelos_assentos)
    ON CONFLICT (id_modelo, numero) DO NOTHING;
  END IF;
END $$;


-- === Guarda-chuvas, Óculos, Toalhas de mesa, Aventais, Luvas, Pegas,
--     Panos de cozinha, Protetor de colchão, Passadeira, Regional ===
-- Mesmo padrão: tabela de cores dedicada (modelo_X_cores) por família.

DO $$
BEGIN
  IF to_regclass('public.modelos_guarda_chuvas') IS NOT NULL THEN
    INSERT INTO product_models (id, id_categoria, tipo_catalogo, nome, slug, descricao, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_categoria, 'guarda_chuva', nome, COALESCE(slug, ''), COALESCE(descricao, ''), '{}'::jsonb,
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM modelos_guarda_chuvas ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.guarda_chuva') IS NOT NULL THEN
    INSERT INTO product_variants (id, id_modelo, tipo_catalogo, ean, barcode_url, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_modelo, 'guarda_chuva', ean, barcode_url, '{}'::jsonb,
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM guarda_chuva ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.modelo_guarda_chuva_cores') IS NOT NULL THEN
    INSERT INTO product_model_colors (id, id_modelo, numero, nome, imagem, visibilidade, created_at)
    SELECT id, id_modelo, numero, COALESCE(nome, ''), COALESCE(imagem, ''), COALESCE(visibilidade, false), COALESCE(created_at, now())
    FROM modelo_guarda_chuva_cores ON CONFLICT (id_modelo, numero) DO NOTHING;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.modelos_oculos') IS NOT NULL THEN
    INSERT INTO product_models (id, id_categoria, tipo_catalogo, nome, slug, descricao, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_categoria, 'oculo', nome, COALESCE(slug, ''), COALESCE(descricao, ''),
           jsonb_build_object('tipo_oculo', tipo_oculo),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM modelos_oculos ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.oculo') IS NOT NULL THEN
    INSERT INTO product_variants (id, id_modelo, tipo_catalogo, ean, barcode_url, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_modelo, 'oculo', ean, barcode_url,
           jsonb_build_object('segmento', segmento),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM oculo ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.modelo_oculo_cores') IS NOT NULL THEN
    INSERT INTO product_model_colors (id, id_modelo, numero, nome, imagem, visibilidade, created_at)
    SELECT id, id_modelo, numero, COALESCE(nome, ''), COALESCE(imagem, ''), COALESCE(visibilidade, false), COALESCE(created_at, now())
    FROM modelo_oculo_cores ON CONFLICT (id_modelo, numero) DO NOTHING;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.modelos_toalhas_mesa') IS NOT NULL THEN
    INSERT INTO product_models (id, id_categoria, tipo_catalogo, nome, slug, descricao, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_categoria, 'toalha_mesa', nome, COALESCE(slug, ''), COALESCE(descricao, ''),
           jsonb_build_object('tipo_produto', tipo_produto, 'material', material, 'composicao', COALESCE(composicao, '{}'::jsonb), 'dimensoes', COALESCE(to_jsonb(dimensoes), '[]'::jsonb)),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM modelos_toalhas_mesa ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.toalha_mesa') IS NOT NULL THEN
    INSERT INTO product_variants (id, id_modelo, tipo_catalogo, ean, barcode_url, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_modelo, 'toalha_mesa', ean, barcode_url,
           jsonb_build_object('dimensoes', dimensoes),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM toalha_mesa ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.modelo_toalha_mesa_cores') IS NOT NULL THEN
    INSERT INTO product_model_colors (id, id_modelo, numero, nome, imagem, visibilidade, created_at)
    SELECT id, id_modelo, numero, COALESCE(nome, ''), COALESCE(imagem, ''), COALESCE(visibilidade, false), COALESCE(created_at, now())
    FROM modelo_toalha_mesa_cores ON CONFLICT (id_modelo, numero) DO NOTHING;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.modelos_aventais') IS NOT NULL THEN
    INSERT INTO product_models (id, id_categoria, tipo_catalogo, nome, slug, descricao, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_categoria, 'avental', nome, COALESCE(slug, ''), COALESCE(descricao, ''),
           jsonb_build_object('composicao', COALESCE(composicao, '{}'::jsonb)),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM modelos_aventais ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.avental') IS NOT NULL THEN
    INSERT INTO product_variants (id, id_modelo, tipo_catalogo, ean, barcode_url, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_modelo, 'avental', ean, barcode_url, '{}'::jsonb,
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM avental ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.modelo_avental_cores') IS NOT NULL THEN
    INSERT INTO product_model_colors (id, id_modelo, numero, nome, imagem, visibilidade, created_at)
    SELECT id, id_modelo, numero, COALESCE(nome, ''), COALESCE(imagem, ''), COALESCE(visibilidade, false), COALESCE(created_at, now())
    FROM modelo_avental_cores ON CONFLICT (id_modelo, numero) DO NOTHING;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.modelos_luvas') IS NOT NULL THEN
    INSERT INTO product_models (id, id_categoria, tipo_catalogo, nome, slug, descricao, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_categoria, 'luva', nome, COALESCE(slug, ''), COALESCE(descricao, ''),
           jsonb_build_object('composicao', COALESCE(composicao, '{}'::jsonb)),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM modelos_luvas ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.luva') IS NOT NULL THEN
    INSERT INTO product_variants (id, id_modelo, tipo_catalogo, ean, barcode_url, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_modelo, 'luva', ean, barcode_url, '{}'::jsonb,
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM luva ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.modelo_luva_cores') IS NOT NULL THEN
    INSERT INTO product_model_colors (id, id_modelo, numero, nome, imagem, visibilidade, created_at)
    SELECT id, id_modelo, numero, COALESCE(nome, ''), COALESCE(imagem, ''), COALESCE(visibilidade, false), COALESCE(created_at, now())
    FROM modelo_luva_cores ON CONFLICT (id_modelo, numero) DO NOTHING;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.modelos_pegas') IS NOT NULL THEN
    INSERT INTO product_models (id, id_categoria, tipo_catalogo, nome, slug, descricao, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_categoria, 'pega', nome, COALESCE(slug, ''), COALESCE(descricao, ''),
           jsonb_build_object('composicao', COALESCE(composicao, '{}'::jsonb)),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM modelos_pegas ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.pega') IS NOT NULL THEN
    INSERT INTO product_variants (id, id_modelo, tipo_catalogo, ean, barcode_url, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_modelo, 'pega', ean, barcode_url, '{}'::jsonb,
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM pega ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.modelo_pega_cores') IS NOT NULL THEN
    INSERT INTO product_model_colors (id, id_modelo, numero, nome, imagem, visibilidade, created_at)
    SELECT id, id_modelo, numero, COALESCE(nome, ''), COALESCE(imagem, ''), COALESCE(visibilidade, false), COALESCE(created_at, now())
    FROM modelo_pega_cores ON CONFLICT (id_modelo, numero) DO NOTHING;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.modelos_panos_cozinha') IS NOT NULL THEN
    INSERT INTO product_models (id, id_categoria, tipo_catalogo, nome, slug, descricao, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_categoria, 'pano_cozinha', nome, COALESCE(slug, ''), COALESCE(descricao, ''),
           jsonb_build_object('composicao', COALESCE(composicao, '{}'::jsonb), 'dimensoes', COALESCE(to_jsonb(dimensoes), '[]'::jsonb)),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM modelos_panos_cozinha ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.pano_cozinha') IS NOT NULL THEN
    INSERT INTO product_variants (id, id_modelo, tipo_catalogo, ean, barcode_url, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_modelo, 'pano_cozinha', ean, barcode_url,
           jsonb_build_object('dimensoes', dimensoes),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM pano_cozinha ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.modelo_pano_cozinha_cores') IS NOT NULL THEN
    INSERT INTO product_model_colors (id, id_modelo, numero, nome, imagem, visibilidade, created_at)
    SELECT id, id_modelo, numero, COALESCE(nome, ''), COALESCE(imagem, ''), COALESCE(visibilidade, false), COALESCE(created_at, now())
    FROM modelo_pano_cozinha_cores ON CONFLICT (id_modelo, numero) DO NOTHING;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.modelos_protetores_colchao') IS NOT NULL THEN
    INSERT INTO product_models (id, id_categoria, tipo_catalogo, nome, slug, descricao, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_categoria, 'protetor_colchao', nome, COALESCE(slug, ''), COALESCE(descricao, ''),
           jsonb_build_object('composicao', COALESCE(composicao, '{}'::jsonb), 'dimensoes', COALESCE(to_jsonb(dimensoes), '[]'::jsonb)),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM modelos_protetores_colchao ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.protetor_colchao') IS NOT NULL THEN
    INSERT INTO product_variants (id, id_modelo, tipo_catalogo, ean, barcode_url, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_modelo, 'protetor_colchao', ean, barcode_url,
           jsonb_build_object('dimensoes', dimensoes),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM protetor_colchao ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.modelo_protetor_colchao_cores') IS NOT NULL THEN
    INSERT INTO product_model_colors (id, id_modelo, numero, nome, imagem, visibilidade, created_at)
    SELECT id, id_modelo, numero, COALESCE(nome, ''), COALESCE(imagem, ''), COALESCE(visibilidade, false), COALESCE(created_at, now())
    FROM modelo_protetor_colchao_cores ON CONFLICT (id_modelo, numero) DO NOTHING;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.modelos_passadeiras') IS NOT NULL THEN
    INSERT INTO product_models (id, id_categoria, tipo_catalogo, nome, slug, descricao, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_categoria, 'passadeira', nome, COALESCE(slug, ''), COALESCE(descricao, ''),
           jsonb_build_object('composicao', COALESCE(composicao, '{}'::jsonb), 'dimensoes', COALESCE(to_jsonb(dimensoes), '[]'::jsonb)),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM modelos_passadeiras ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.passadeira') IS NOT NULL THEN
    INSERT INTO product_variants (id, id_modelo, tipo_catalogo, ean, barcode_url, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_modelo, 'passadeira', ean, barcode_url,
           jsonb_build_object('dimensoes', dimensoes),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM passadeira ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.modelo_passadeira_cores') IS NOT NULL THEN
    INSERT INTO product_model_colors (id, id_modelo, numero, nome, imagem, visibilidade, created_at)
    SELECT id, id_modelo, numero, COALESCE(nome, ''), COALESCE(imagem, ''), COALESCE(visibilidade, false), COALESCE(created_at, now())
    FROM modelo_passadeira_cores ON CONFLICT (id_modelo, numero) DO NOTHING;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.modelos_regionais') IS NOT NULL THEN
    INSERT INTO product_models (id, id_categoria, tipo_catalogo, nome, slug, descricao, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_categoria, 'regional', nome, COALESCE(slug, ''), COALESCE(descricao, ''),
           jsonb_build_object('subtipo', subtipo, 'composicao', COALESCE(composicao, '{}'::jsonb), 'dimensoes', COALESCE(to_jsonb(dimensoes), 'null'::jsonb)),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM modelos_regionais ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.regional') IS NOT NULL THEN
    INSERT INTO product_variants (id, id_modelo, tipo_catalogo, ean, barcode_url, attributes, visibilidade, created_at, updated_at)
    SELECT id, id_modelo, 'regional', ean, barcode_url,
           jsonb_build_object('dimensoes', dimensoes),
           COALESCE(visibilidade, false), COALESCE(created_at, now()), now()  -- tabela legada sem updated_at
    FROM regional ON CONFLICT (id) DO NOTHING;
  END IF;
  IF to_regclass('public.modelo_regional_cores') IS NOT NULL THEN
    INSERT INTO product_model_colors (id, id_modelo, numero, nome, imagem, visibilidade, created_at)
    SELECT id, id_modelo, numero, COALESCE(nome, ''), COALESCE(imagem, ''), COALESCE(visibilidade, false), COALESCE(created_at, now())
    FROM modelo_regional_cores ON CONFLICT (id_modelo, numero) DO NOTHING;
  END IF;
END $$;


-- ============================================================================
-- PASSO 3 — verificação (corre antes de COMMIT; compara os totais)
-- ============================================================================
-- Ajusta a lista de tabelas antigas consoante o que existir de facto na tua BD.

-- SELECT 'modelos_almofadas' AS tabela, count(*) FROM modelos_almofadas
-- UNION ALL SELECT 'product_models (almofada)', count(*) FROM product_models WHERE tipo_catalogo = 'almofada'
-- UNION ALL SELECT 'almofada', count(*) FROM almofada
-- UNION ALL SELECT 'product_variants (almofada)', count(*) FROM product_variants WHERE tipo_catalogo = 'almofada';
--
-- Repete para cada família, e confirma:
--   SELECT count(*) FROM product_models;   -- deve bater com a soma de todos os modelos_X antigos
--   SELECT count(*) FROM product_variants; -- deve bater com a soma de todos os produtos antigos
--   SELECT count(*) FROM product_model_colors;
-- ============================================================================
