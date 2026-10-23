-- ============================================================================
-- 0001: esquema de catálogo unificado
-- ============================================================================
-- Substitui as 13 famílias de tabelas (modelos_X / X / modelo_X_cores) por 3
-- tabelas partilhadas por todas as categorias, discriminadas por
-- `tipo_catalogo`. Os campos que variavam por família (tipo, composição,
-- dimensões, altura, ...) vivem agora em `attributes jsonb`, validados em
-- Python (models/catalog_attributes.py) antes de chegarem à BD.
--
-- SEGURO DE CORRER MAIS DO QUE UMA VEZ (idempotente: IF NOT EXISTS / DROP+CREATE
-- em policies). NÃO apaga nem toca nas 13 tabelas antigas — essas só são
-- tocadas no passo 0002 (migração de dados) e no cleanup final, que são
-- passos manuais e deliberados.
--
-- Corre isto no Supabase SQL Editor (ou psql) ANTES do 0002.
-- ============================================================================

-- === Tabelas ===

CREATE TABLE IF NOT EXISTS product_models (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_categoria uuid NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    tipo_catalogo text NOT NULL,
    nome text NOT NULL,
    slug text DEFAULT '',
    descricao text DEFAULT '',
    attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
    visibilidade boolean NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS product_model_colors (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_modelo uuid NOT NULL REFERENCES product_models(id) ON DELETE CASCADE,
    numero integer NOT NULL,
    nome text DEFAULT '',
    imagem text NOT NULL DEFAULT '',
    visibilidade boolean NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    UNIQUE (id_modelo, numero)
);

CREATE TABLE IF NOT EXISTS product_variants (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_modelo uuid NOT NULL REFERENCES product_models(id) ON DELETE CASCADE,
    tipo_catalogo text NOT NULL,
    ean text NOT NULL,
    barcode_url text,
    attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
    visibilidade boolean NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- === Índices ===
-- (substituem os ~36 índices por-família antigos por ~8 índices partilhados;
--  cobrem exactamente os filtros que a loja e o backoffice fazem sempre:
--  categoria+visibilidade, tipo_catalogo, slug, EAN, atributos.)

CREATE INDEX IF NOT EXISTS idx_product_models_categoria ON product_models (id_categoria);
CREATE INDEX IF NOT EXISTS idx_product_models_tipo ON product_models (tipo_catalogo);
CREATE INDEX IF NOT EXISTS idx_product_models_cat_vis_created
  ON product_models (id_categoria, visibilidade, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_product_models_visible
  ON product_models (id_categoria, created_at DESC) WHERE visibilidade = true;
CREATE INDEX IF NOT EXISTS idx_product_models_slug ON product_models (slug);
CREATE INDEX IF NOT EXISTS idx_product_models_attributes ON product_models USING GIN (attributes);

CREATE INDEX IF NOT EXISTS idx_product_model_colors_modelo ON product_model_colors (id_modelo);
CREATE INDEX IF NOT EXISTS idx_product_model_colors_created ON product_model_colors (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_product_variants_modelo ON product_variants (id_modelo);
CREATE INDEX IF NOT EXISTS idx_product_variants_modelo_vis ON product_variants (id_modelo, visibilidade);
CREATE INDEX IF NOT EXISTS idx_product_variants_tipo ON product_variants (tipo_catalogo);
CREATE INDEX IF NOT EXISTS idx_product_variants_created ON product_variants (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_product_variants_attributes ON product_variants USING GIN (attributes);
CREATE UNIQUE INDEX IF NOT EXISTS uq_product_variants_ean
  ON product_variants (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';

-- === updated_at triggers ===
-- (reaproveita a função diomika_set_updated_at já criada em production_setup.sql)

DROP TRIGGER IF EXISTS trg_product_models_updated_at ON product_models;
CREATE TRIGGER trg_product_models_updated_at
  BEFORE UPDATE ON product_models FOR EACH ROW EXECUTE FUNCTION diomika_set_updated_at();

DROP TRIGGER IF EXISTS trg_product_variants_updated_at ON product_variants;
CREATE TRIGGER trg_product_variants_updated_at
  BEFORE UPDATE ON product_variants FOR EACH ROW EXECUTE FUNCTION diomika_set_updated_at();

-- === RLS: só leitura pública de registos visíveis; escrita só service_role ===

ALTER TABLE product_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_model_colors ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_variants ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "product_models_public_read" ON product_models;
CREATE POLICY "product_models_public_read" ON product_models
  FOR SELECT TO anon USING (visibilidade = true);
DROP POLICY IF EXISTS "product_models_deny_anon_write" ON product_models;
CREATE POLICY "product_models_deny_anon_write" ON product_models
  FOR INSERT TO anon WITH CHECK (false);
DROP POLICY IF EXISTS "product_models_deny_anon_update" ON product_models;
CREATE POLICY "product_models_deny_anon_update" ON product_models
  FOR UPDATE TO anon USING (false) WITH CHECK (false);
DROP POLICY IF EXISTS "product_models_deny_anon_delete" ON product_models;
CREATE POLICY "product_models_deny_anon_delete" ON product_models
  FOR DELETE TO anon USING (false);

DROP POLICY IF EXISTS "product_model_colors_public_read" ON product_model_colors;
CREATE POLICY "product_model_colors_public_read" ON product_model_colors
  FOR SELECT TO anon USING (visibilidade = true);
DROP POLICY IF EXISTS "product_model_colors_deny_anon_write" ON product_model_colors;
CREATE POLICY "product_model_colors_deny_anon_write" ON product_model_colors
  FOR INSERT TO anon WITH CHECK (false);
DROP POLICY IF EXISTS "product_model_colors_deny_anon_update" ON product_model_colors;
CREATE POLICY "product_model_colors_deny_anon_update" ON product_model_colors
  FOR UPDATE TO anon USING (false) WITH CHECK (false);
DROP POLICY IF EXISTS "product_model_colors_deny_anon_delete" ON product_model_colors;
CREATE POLICY "product_model_colors_deny_anon_delete" ON product_model_colors
  FOR DELETE TO anon USING (false);

DROP POLICY IF EXISTS "product_variants_public_read" ON product_variants;
CREATE POLICY "product_variants_public_read" ON product_variants
  FOR SELECT TO anon USING (visibilidade = true);
DROP POLICY IF EXISTS "product_variants_deny_anon_write" ON product_variants;
CREATE POLICY "product_variants_deny_anon_write" ON product_variants
  FOR INSERT TO anon WITH CHECK (false);
DROP POLICY IF EXISTS "product_variants_deny_anon_update" ON product_variants;
CREATE POLICY "product_variants_deny_anon_update" ON product_variants
  FOR UPDATE TO anon USING (false) WITH CHECK (false);
DROP POLICY IF EXISTS "product_variants_deny_anon_delete" ON product_variants;
CREATE POLICY "product_variants_deny_anon_delete" ON product_variants
  FOR DELETE TO anon USING (false);

-- === Lookup EAN unificado (checkout / pesquisa / PDFs) ===
-- Substitui a view antiga (UNION ALL de 13 tabelas) por uma simples select.

DROP VIEW IF EXISTS catalog_ean_lookup;
CREATE VIEW catalog_ean_lookup WITH (security_invoker = true) AS
SELECT
    v.tipo_catalogo AS tipo,
    v.id AS product_id,
    v.ean,
    v.id_modelo,
    v.visibilidade AS product_visivel,
    m.visibilidade AS model_visivel
FROM product_variants v
JOIN product_models m ON m.id = v.id_modelo
WHERE v.ean IS NOT NULL AND btrim(v.ean) <> '';

-- === Realtime (postgres_changes na loja) ===

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'product_models'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.product_models;
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'product_variants'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.product_variants;
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'product_model_colors'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.product_model_colors;
  END IF;
END $$;
