-- ============================================================================
-- Base de dados: privilégios, RLS, Storage, Realtime, índices, restrições
-- (auditoria BD-05, BD-06, BD-07, BD-08, BD-09, BD-11, BD-12)
-- ============================================================================
-- Idempotente: pode correr duas vezes. Não apaga dados (só normaliza maiúsculas nos emails, ver BD-11).
-- A limpeza do schema `backup` (BD-10) está à parte, em 2026-11-02_drop_backup_schema.sql, por ser um DROP.
--
-- ORDEM: aplicar DEPOIS de 2026-11-02_new_columns.sql e ANTES da API nova (a API passa a gravar os emails em
-- minúsculas, que é o que o CHECK exige). Faz-se num SQL Editor/apply_migration com a service_role/postgres.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- BD-05: anon e authenticated não precisam de TRUNCATE, REFERENCES, TRIGGER nem MAINTAIN.
-- A RLS não cobre o TRUNCATE; é defesa em profundidade.
-- ----------------------------------------------------------------------------
REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLES FROM anon, authenticated;

-- MAINTAIN só existe a partir do Postgres 17 (a produção é 17.6).
DO $do$
BEGIN
  IF current_setting('server_version_num')::int >= 170000 THEN
    EXECUTE 'REVOKE MAINTAIN ON ALL TABLES IN SCHEMA public FROM anon, authenticated';
    EXECUTE 'ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE MAINTAIN ON TABLES FROM anon, authenticated';
  END IF;
END
$do$;

-- As escritas do catálogo são todas feitas pela API (service_role): o anon só lê.
REVOKE INSERT, UPDATE, DELETE ON public.categories, public.product_models, public.product_variants,
  public.product_model_colors FROM anon;

-- ----------------------------------------------------------------------------
-- BD-06: a leitura pública só vale se o pai também for público (a cascata da API deixava de ser a única guarda).
-- ALTER POLICY mantém o papel (TO anon) e o comando (SELECT) de cada política.
-- ----------------------------------------------------------------------------
ALTER POLICY product_models_public_read ON public.product_models
  USING (visibilidade AND EXISTS (SELECT 1 FROM public.categories c WHERE c.id = id_categoria AND c.visibilidade));
ALTER POLICY product_variants_public_read ON public.product_variants
  USING (visibilidade AND EXISTS (SELECT 1 FROM public.product_models m WHERE m.id = id_modelo AND m.visibilidade));
ALTER POLICY product_model_colors_public_read ON public.product_model_colors
  USING (visibilidade AND EXISTS (SELECT 1 FROM public.product_models m WHERE m.id = id_modelo AND m.visibilidade));

-- ----------------------------------------------------------------------------
-- BD-07: sem listagem pública do bucket de fotos (os URLs públicos continuam a abrir sem política);
-- limite de tamanho e de tipos no próprio bucket (a API já valida, isto é a segunda barreira).
-- Os buckets `barcodes` e `public` (sem uso) esvaziam-se e apagam-se pelo painel: o Storage não deixa
-- apagar buckets por SQL.
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS product_images_public_read ON storage.objects;

UPDATE storage.buckets
   SET file_size_limit = 5 * 1024 * 1024,
       allowed_mime_types = ARRAY['image/png', 'image/jpeg', 'image/webp', 'image/gif']
 WHERE id = 'product-images';

-- ----------------------------------------------------------------------------
-- BD-08: Realtime sem uso (as subscrições saíram do código a 2026-10-21). Menos carga e menos superfície.
-- ----------------------------------------------------------------------------
DO $do$
DECLARE
  r record;
BEGIN
  FOR r IN
    SELECT schemaname, tablename FROM pg_publication_tables
     WHERE pubname = 'supabase_realtime' AND schemaname = 'public'
       AND tablename IN ('categories', 'contact_messages', 'message_history',
                         'product_models', 'product_variants', 'product_model_colors')
  LOOP
    EXECUTE format('ALTER PUBLICATION supabase_realtime DROP TABLE %I.%I', r.schemaname, r.tablename);
  END LOOP;
END
$do$;

-- ----------------------------------------------------------------------------
-- BD-09: índices duplicados, prefixos de índices compostos e GIN que o filtro usado não aproveita.
-- Fica idx_message_history_message_id (serve a FK com ON DELETE CASCADE).
-- ----------------------------------------------------------------------------
DROP INDEX IF EXISTS public.idx_categories_slug;            -- cópia de categories_slug_key
DROP INDEX IF EXISTS public.idx_product_models_categoria;   -- prefixo de idx_product_models_cat_vis_created
DROP INDEX IF EXISTS public.idx_product_variants_modelo;    -- prefixo de idx_product_variants_modelo_vis
DROP INDEX IF EXISTS public.idx_product_model_colors_modelo; -- prefixo de product_model_colors_id_modelo_numero_key
DROP INDEX IF EXISTS public.idx_product_models_attributes;
DROP INDEX IF EXISTS public.idx_product_variants_attributes;

-- ----------------------------------------------------------------------------
-- BD-11: restrições que faltavam.
-- ----------------------------------------------------------------------------

-- Slugs: ASCII minúsculo, sem vazios, únicos por categoria. A loja resolve o modelo por slug com limit(1):
-- um duplicado torna um dos dois inalcançável. Primeiro corrige-se o que não cumpre.
UPDATE public.product_models
   SET slug = coalesce(nullif(trim(both '-' from regexp_replace(
         translate(lower(CASE WHEN coalesce(slug, '') = '' THEN nome ELSE slug END),
                   'áàâãäåçéèêëíìîïñóòôõöúùûüýÿ', 'aaaaaaceeeeiiiinooooouuuuyy'),
         '[^a-z0-9]+', '-', 'g')), ''), 'modelo')
 WHERE slug IS NULL OR slug !~ '^[a-z0-9-]+$';

-- Duplicados dentro da mesma categoria: o mais antigo fica com o slug, os outros ganham -2, -3...
WITH d AS (
  SELECT id, row_number() OVER (PARTITION BY id_categoria, slug ORDER BY created_at, id) AS rn
    FROM public.product_models
)
UPDATE public.product_models m
   SET slug = m.slug || '-' || d.rn
  FROM d
 WHERE d.id = m.id AND d.rn > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_product_models_cat_slug ON public.product_models (id_categoria, slug);

ALTER TABLE public.product_models DROP CONSTRAINT IF EXISTS ck_product_models_slug;
ALTER TABLE public.product_models ADD CONSTRAINT ck_product_models_slug CHECK (slug ~ '^[a-z0-9-]+$');

-- Emails sempre em minúsculas: o apagamento RGPD compara por lower(email) e a BD passa a garantir o formato.
-- (Normalizar o que existe não muda a quem pertence o endereço.)
UPDATE public.contact_messages SET email = lower(email) WHERE email <> lower(email);
UPDATE public.pedidos_orcamento SET email = lower(email) WHERE email <> lower(email);

ALTER TABLE public.contact_messages DROP CONSTRAINT IF EXISTS ck_contact_email_lower;
ALTER TABLE public.contact_messages ADD CONSTRAINT ck_contact_email_lower CHECK (email = lower(email));
ALTER TABLE public.pedidos_orcamento DROP CONSTRAINT IF EXISTS ck_pedidos_email_lower;
ALTER TABLE public.pedidos_orcamento ADD CONSTRAINT ck_pedidos_email_lower CHECK (email = lower(email));

-- A família de uma categoria nunca se presume (o DEFAULT 'almofada' criava categorias na família errada).
ALTER TABLE public.categories ALTER COLUMN tipo_catalogo DROP DEFAULT;
ALTER TABLE public.categories DROP CONSTRAINT IF EXISTS ck_categories_tipo_slug;
ALTER TABLE public.categories ADD CONSTRAINT ck_categories_tipo_slug CHECK (tipo_catalogo ~ '^[a-z][a-z0-9_]*$');

-- Estados: lista fechada, com os terminais da retenção e os que o backoffice vai usar (tarefa 2.7).
-- NOT VALID: vale já para linhas novas; se alguma linha antiga tiver outro estado, a validação avisa e deixa
-- a restrição a valer só para o futuro (em vez de falhar a migração toda).
ALTER TABLE public.pedidos_orcamento DROP CONSTRAINT IF EXISTS ck_pedidos_orcamento_status;
ALTER TABLE public.pedidos_orcamento ADD CONSTRAINT ck_pedidos_orcamento_status
  CHECK (status IN ('Nova', 'Email pendente', 'Em tratamento', 'Vendido', 'Cancelado', 'Arquivado', 'Rejeitado')) NOT VALID;
ALTER TABLE public.contact_messages DROP CONSTRAINT IF EXISTS ck_contact_messages_status;
ALTER TABLE public.contact_messages ADD CONSTRAINT ck_contact_messages_status
  CHECK (status IN ('Nova', 'Email pendente', 'Em conversa', 'Respondida', 'Arquivado')) NOT VALID;

DO $do$
BEGIN
  BEGIN
    ALTER TABLE public.pedidos_orcamento VALIDATE CONSTRAINT ck_pedidos_orcamento_status;
  EXCEPTION WHEN check_violation THEN
    RAISE WARNING 'pedidos_orcamento tem estados fora da lista: a restrição vale só para linhas novas';
  END;
  BEGIN
    ALTER TABLE public.contact_messages VALIDATE CONSTRAINT ck_contact_messages_status;
  EXCEPTION WHEN check_violation THEN
    RAISE WARNING 'contact_messages tem estados fora da lista: a restrição vale só para linhas novas';
  END;
END
$do$;

-- ----------------------------------------------------------------------------
-- BD-12: apagar uma categoria já não leva o catálogo atrás. É preciso esvaziá-la primeiro.
-- (modelos -> variantes/cores continuam em CASCADE: apagar um modelo apaga o que é dele.)
-- ----------------------------------------------------------------------------
ALTER TABLE public.product_models DROP CONSTRAINT IF EXISTS product_models_id_categoria_fkey;
ALTER TABLE public.product_models ADD CONSTRAINT product_models_id_categoria_fkey
  FOREIGN KEY (id_categoria) REFERENCES public.categories(id) ON DELETE RESTRICT;
