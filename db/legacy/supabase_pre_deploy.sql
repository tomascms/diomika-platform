-- Bundle idempotente — colar no Supabase SQL Editor antes do deploy
-- Projecto: https://app.supabase.com/project/your-project-ref/sql/new
--
-- BD actual: tabela almofada (não products). Script idempotente.

-- Colunas de carrinho (categorias)
ALTER TABLE categories ADD COLUMN IF NOT EXISTS carrinho_step integer DEFAULT 6;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS carrinho_min integer DEFAULT 6;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS tipo_catalogo text NOT NULL DEFAULT 'almofada';

ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_slug_key;
ALTER TABLE categories ADD CONSTRAINT categories_slug_key UNIQUE (slug);

UPDATE categories SET tipo_catalogo = 'assento' WHERE slug IN ('assentos', 'assento');
UPDATE categories SET tipo_catalogo = 'almofada' WHERE slug IN ('almofadas', 'almofada') AND tipo_catalogo IS NULL;
UPDATE categories SET tipo_catalogo = 'almofada' WHERE tipo_catalogo IS NULL;

-- Validação de tipo_catalogo feita na API (CATALOG_TYPES) — sem CHECK estático na BD
ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_tipo_catalogo_check;

ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_carrinho_step_check;
ALTER TABLE categories ADD CONSTRAINT categories_carrinho_step_check CHECK (carrinho_step IS NULL OR carrinho_step > 0);

ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_carrinho_min_check;
ALTER TABLE categories ADD CONSTRAINT categories_carrinho_min_check CHECK (carrinho_min IS NULL OR carrinho_min > 0);

-- Composição no modelo
ALTER TABLE modelos_almofadas ADD COLUMN IF NOT EXISTS composicao jsonb DEFAULT '{}'::jsonb;

-- Cores por modelo
CREATE TABLE IF NOT EXISTS modelo_cores (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_modelo uuid NOT NULL REFERENCES modelos_almofadas(id) ON DELETE CASCADE,
    numero integer NOT NULL,
    nome text DEFAULT '',
    imagem text NOT NULL DEFAULT '',
    visibilidade boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    UNIQUE (id_modelo, numero)
);

-- Orçamentos (site) e encomendas (backoffice)
CREATE TABLE IF NOT EXISTS pedidos_orcamento (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nome text NOT NULL,
    email text NOT NULL,
    contacto text,
    empresa text,
    observacoes text,
    linhas jsonb NOT NULL DEFAULT '[]'::jsonb,
    lida boolean DEFAULT false,
    visibilidade boolean DEFAULT true,
    status text DEFAULT 'Nova',
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS encomendas_internas (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    referencia_cliente text NOT NULL,
    observacoes text,
    linhas jsonb NOT NULL DEFAULT '[]'::jsonb,
    visibilidade boolean DEFAULT true,
    created_at timestamptz DEFAULT now()
);

-- === production_setup.sql (infra + RLS) ===

CREATE TABLE IF NOT EXISTS outbox_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}',
    status text NOT NULL DEFAULT 'pending',
    attempts int NOT NULL DEFAULT 0,
    max_attempts int NOT NULL DEFAULT 5,
    next_retry_at timestamptz DEFAULT now(),
    last_error text,
    created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_outbox_pending ON outbox_events (status, next_retry_at);
ALTER TABLE outbox_events ADD COLUMN IF NOT EXISTS claimed_by text;
ALTER TABLE outbox_events ADD COLUMN IF NOT EXISTS claimed_at timestamptz;
CREATE INDEX IF NOT EXISTS idx_outbox_processing ON outbox_events (status, claimed_at)
  WHERE status = 'processing';

CREATE TABLE IF NOT EXISTS saga_instances (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    saga_type text NOT NULL,
    status text NOT NULL DEFAULT 'running',
    current_step text,
    context jsonb DEFAULT '{}',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key text PRIMARY KEY,
    operation text NOT NULL,
    response jsonb NOT NULL,
    created_at timestamptz DEFAULT now(),
    expires_at timestamptz
);
CREATE INDEX IF NOT EXISTS idx_idempotency_expires ON idempotency_keys (expires_at);

ALTER TABLE categories ALTER COLUMN slug SET NOT NULL;
ALTER TABLE categories ALTER COLUMN imagem SET NOT NULL;
ALTER TABLE categories ALTER COLUMN visibilidade SET DEFAULT true;

ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE modelos_almofadas ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS almofada ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS modelo_cores ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS pedidos_orcamento ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS encomendas_internas ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS contact_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS message_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE saga_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "categories_public_read" ON categories;
CREATE POLICY "categories_public_read" ON categories FOR SELECT TO anon USING (visibilidade = true);

DROP POLICY IF EXISTS "modelos_public_read" ON modelos_almofadas;
CREATE POLICY "modelos_public_read" ON modelos_almofadas FOR SELECT TO anon USING (visibilidade = true);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'almofada') THEN
        DROP POLICY IF EXISTS "almofada_public_read" ON almofada;
        CREATE POLICY "almofada_public_read" ON almofada FOR SELECT TO anon USING (visibilidade = true);
    END IF;
END $$;

DROP POLICY IF EXISTS "modelo_cores_public_read" ON modelo_cores;
CREATE POLICY "modelo_cores_public_read" ON modelo_cores FOR SELECT TO anon USING (visibilidade = true);

DROP POLICY IF EXISTS "pedidos_orcamento_deny_anon" ON pedidos_orcamento;
CREATE POLICY "pedidos_orcamento_deny_anon" ON pedidos_orcamento FOR ALL TO anon USING (false);

DROP POLICY IF EXISTS "encomendas_internas_deny_anon" ON encomendas_internas;
CREATE POLICY "encomendas_internas_deny_anon" ON encomendas_internas FOR ALL TO anon USING (false);

DROP POLICY IF EXISTS "contact_public_insert" ON contact_messages;
DROP POLICY IF EXISTS "contact_deny_anon_insert" ON contact_messages;
CREATE POLICY "contact_deny_anon_insert" ON contact_messages FOR INSERT TO anon WITH CHECK (false);

DROP POLICY IF EXISTS "contact_deny_anon_select" ON contact_messages;
CREATE POLICY "contact_deny_anon_select" ON contact_messages FOR SELECT TO anon USING (false);

DROP POLICY IF EXISTS "history_deny_anon" ON message_history;
CREATE POLICY "history_deny_anon" ON message_history FOR ALL TO anon USING (false);

DROP POLICY IF EXISTS "outbox_deny_anon" ON outbox_events;
CREATE POLICY "outbox_deny_anon" ON outbox_events FOR ALL TO anon USING (false);

DROP POLICY IF EXISTS "saga_deny_anon" ON saga_instances;
CREATE POLICY "saga_deny_anon" ON saga_instances FOR ALL TO anon USING (false);

DROP POLICY IF EXISTS "idempotency_deny_anon" ON idempotency_keys;
CREATE POLICY "idempotency_deny_anon" ON idempotency_keys FOR ALL TO anon USING (false);

DROP POLICY IF EXISTS "product_images_public_read" ON storage.objects;
CREATE POLICY "product_images_public_read" ON storage.objects
  FOR SELECT TO anon
  USING (
    bucket_id = 'product-images'
    AND coalesce(name, '') <> ''
    AND right(name, 1) <> '/'
  );

DROP POLICY IF EXISTS "product_images_no_anon_write" ON storage.objects;
CREATE POLICY "product_images_no_anon_write" ON storage.objects FOR INSERT TO anon WITH CHECK (false);

DROP POLICY IF EXISTS "product_images_no_anon_update" ON storage.objects;
CREATE POLICY "product_images_no_anon_update" ON storage.objects FOR UPDATE TO anon USING (false);

DROP POLICY IF EXISTS "product_images_no_anon_delete" ON storage.objects;
CREATE POLICY "product_images_no_anon_delete" ON storage.objects FOR DELETE TO anon USING (false);

-- barcodes: SELECT anon para signed URLs; escrita só service_role
DROP POLICY IF EXISTS "barcodes_public_read" ON storage.objects;
CREATE POLICY "barcodes_public_read" ON storage.objects
  FOR SELECT TO anon
  USING (
    bucket_id = 'barcodes'
    AND coalesce(name, '') <> ''
    AND right(name, 1) <> '/'
  );

DROP POLICY IF EXISTS "barcodes_no_anon_write" ON storage.objects;
CREATE POLICY "barcodes_no_anon_write" ON storage.objects FOR INSERT TO anon WITH CHECK (false);

DROP POLICY IF EXISTS "barcodes_no_anon_update" ON storage.objects;
CREATE POLICY "barcodes_no_anon_update" ON storage.objects FOR UPDATE TO anon USING (false);

DROP POLICY IF EXISTS "barcodes_no_anon_delete" ON storage.objects;
CREATE POLICY "barcodes_no_anon_delete" ON storage.objects FOR DELETE TO anon USING (false);

-- === Assentos (sem paletas — cores em modelo_cores.id_modelo) ===
-- Categorias são criadas apenas no backoffice — sem INSERT automático.

CREATE TABLE IF NOT EXISTS modelos_assentos (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_categoria uuid NOT NULL REFERENCES categories(id),
    nome text NOT NULL,
    slug text DEFAULT '',
    descricao text DEFAULT '',
    material_forro text NOT NULL DEFAULT '',
    material_enchimento text NOT NULL DEFAULT '',
    alturas jsonb NOT NULL DEFAULT '[]'::jsonb,
    visibilidade boolean DEFAULT true,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS assento (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_modelo uuid NOT NULL REFERENCES modelos_assentos(id) ON DELETE CASCADE,
    ean text NOT NULL UNIQUE,
    barcode_url text,
    visibilidade boolean DEFAULT true,
    created_at timestamptz DEFAULT now()
);

-- Compat: BD antigas com paletas / id_categoria no produto
ALTER TABLE modelo_cores DROP CONSTRAINT IF EXISTS modelo_cores_id_modelo_fkey;
ALTER TABLE modelo_cores DROP CONSTRAINT IF EXISTS modelo_cores_owner_check;
DROP INDEX IF EXISTS modelo_cores_paleta_numero_idx;
DROP INDEX IF EXISTS idx_modelo_cores_paleta;
ALTER TABLE modelo_cores DROP COLUMN IF EXISTS template_modelo;
ALTER TABLE modelo_cores DROP COLUMN IF EXISTS id_paleta;
DELETE FROM modelo_cores WHERE id_modelo IS NULL;
ALTER TABLE modelo_cores ALTER COLUMN id_modelo SET NOT NULL;
DROP INDEX IF EXISTS modelo_cores_model_numero_idx;
CREATE UNIQUE INDEX IF NOT EXISTS modelo_cores_model_numero_idx ON modelo_cores (id_modelo, numero);
ALTER TABLE modelos_assentos DROP COLUMN IF EXISTS id_paleta;
ALTER TABLE almofada DROP COLUMN IF EXISTS id_categoria;
ALTER TABLE assento DROP COLUMN IF EXISTS id_categoria;
DROP TABLE IF EXISTS paletas_cores CASCADE;
DROP TABLE IF EXISTS paleta_cores CASCADE;
DROP TABLE IF EXISTS modelo_assento_cores CASCADE;

ALTER TABLE modelos_assentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE assento ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "modelos_assentos_public_read" ON modelos_assentos;
CREATE POLICY "modelos_assentos_public_read" ON modelos_assentos FOR SELECT TO anon USING (visibilidade = true);

DROP POLICY IF EXISTS "assento_public_read" ON assento;
CREATE POLICY "assento_public_read" ON assento FOR SELECT TO anon USING (visibilidade = true);

-- Índices de catálogo (consultas da loja e backoffice)
CREATE INDEX IF NOT EXISTS idx_categories_tipo ON categories (tipo_catalogo);
CREATE INDEX IF NOT EXISTS idx_modelos_almofadas_categoria ON modelos_almofadas (id_categoria);
CREATE INDEX IF NOT EXISTS idx_modelos_assentos_categoria ON modelos_assentos (id_categoria);
CREATE INDEX IF NOT EXISTS idx_almofada_modelo ON almofada (id_modelo);
CREATE INDEX IF NOT EXISTS idx_almofada_ean ON almofada (ean);
CREATE INDEX IF NOT EXISTS idx_assento_modelo ON assento (id_modelo);
CREATE INDEX IF NOT EXISTS idx_assento_ean ON assento (ean);
CREATE INDEX IF NOT EXISTS idx_modelo_cores_modelo ON modelo_cores (id_modelo);

-- === Segurança produção ===
-- Contacto só via API (Turnstile + rate limit); bloquear INSERT anon directo
DROP POLICY IF EXISTS "contact_public_insert" ON contact_messages;
DROP POLICY IF EXISTS "contact_deny_anon_insert" ON contact_messages;
CREATE POLICY "contact_deny_anon_insert" ON contact_messages
  FOR INSERT TO anon WITH CHECK (false);

-- updated_at no catálogo — detecção de conflitos entre vários PCs com backoffice
ALTER TABLE categories ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();
ALTER TABLE modelos_almofadas ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();
ALTER TABLE modelos_assentos ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();
ALTER TABLE almofada ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();
ALTER TABLE assento ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();
ALTER TABLE modelo_cores ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();

CREATE OR REPLACE FUNCTION diomika_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DO $$
DECLARE
  tbl text;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'categories', 'modelos_almofadas', 'modelos_assentos',
    'almofada', 'assento', 'modelo_cores'
  ]
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%I_updated_at ON %I', tbl, tbl);
    EXECUTE format(
      'CREATE TRIGGER trg_%I_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION diomika_set_updated_at()',
      tbl, tbl
    );
  END LOOP;
END $$;

-- === Optimização consultas (loja + backoffice + infra) ===
CREATE INDEX IF NOT EXISTS idx_categories_visible_tipo
  ON categories (tipo_catalogo) WHERE visibilidade = true;

CREATE INDEX IF NOT EXISTS idx_pedidos_orcamento_created
  ON pedidos_orcamento (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_encomendas_created
  ON encomendas_internas (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_contact_messages_created
  ON contact_messages (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_contact_messages_email
  ON contact_messages (lower(email));

CREATE INDEX IF NOT EXISTS idx_pedidos_orcamento_email
  ON pedidos_orcamento (lower(email));

CREATE INDEX IF NOT EXISTS idx_saga_running
  ON saga_instances (updated_at) WHERE status = 'running';

-- === Auditoria admin (backoffice local) ===
CREATE TABLE IF NOT EXISTS admin_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    resource_id TEXT,
    role TEXT NOT NULL DEFAULT 'admin',
    actor TEXT,
    request_id TEXT,
    client_ip TEXT,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb
);
ALTER TABLE admin_audit_log ADD COLUMN IF NOT EXISTS actor TEXT;
CREATE INDEX IF NOT EXISTS idx_admin_audit_created ON admin_audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_resource ON admin_audit_log (resource, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_actor ON admin_audit_log (actor, created_at DESC);
ALTER TABLE admin_audit_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "admin_audit_deny_anon" ON admin_audit_log;
CREATE POLICY "admin_audit_deny_anon" ON admin_audit_log FOR ALL TO anon USING (false);

-- === Realtime (postgres_changes na loja) ===
DO $$
DECLARE
  tbl text;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'categories',
    'modelos_almofadas',
    'almofada',
    'modelos_assentos',
    'assento',
    'modelo_cores'
  ]
  LOOP
    IF to_regclass('public.' || tbl) IS NOT NULL AND NOT EXISTS (
      SELECT 1
      FROM pg_publication_tables
      WHERE pubname = 'supabase_realtime'
        AND schemaname = 'public'
        AND tablename = tbl
    ) THEN
      EXECUTE format('ALTER PUBLICATION supabase_realtime ADD TABLE public.%I', tbl);
    END IF;
  END LOOP;
END $$;

-- === Assento por altura + tipo_catalogo em modelo_cores ===
ALTER TABLE assento ADD COLUMN IF NOT EXISTS altura text;
ALTER TABLE modelo_cores ADD COLUMN IF NOT EXISTS tipo_catalogo text;

UPDATE modelo_cores mc
SET tipo_catalogo = 'almofada'
FROM modelos_almofadas m
WHERE mc.id_modelo = m.id
  AND (mc.tipo_catalogo IS NULL OR mc.tipo_catalogo = '');

UPDATE modelo_cores mc
SET tipo_catalogo = 'assento'
FROM modelos_assentos m
WHERE mc.id_modelo = m.id
  AND (mc.tipo_catalogo IS NULL OR mc.tipo_catalogo = '');

DO $$
DECLARE
  r record;
  first_alt text;
BEGIN
  FOR r IN
    SELECT a.id, m.alturas
    FROM assento a
    JOIN modelos_assentos m ON m.id = a.id_modelo
    WHERE a.altura IS NULL OR trim(a.altura) = ''
  LOOP
    first_alt := NULL;
    IF jsonb_typeof(r.alturas) = 'array' AND jsonb_array_length(r.alturas) > 0 THEN
      first_alt := trim(both '"' from (r.alturas->>0));
    END IF;
    IF first_alt IS NOT NULL AND first_alt <> '' THEN
      UPDATE assento SET altura = first_alt WHERE id = r.id;
    END IF;
  END LOOP;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS assento_modelo_altura_idx
  ON assento (id_modelo, altura)
  WHERE altura IS NOT NULL AND altura <> '';

ALTER TABLE assento DROP CONSTRAINT IF EXISTS assento_id_modelo_key;

CREATE INDEX IF NOT EXISTS idx_modelo_cores_tipo_modelo
  ON modelo_cores (tipo_catalogo, id_modelo);

-- === Assento por altura + tipo_catalogo em modelo_cores ===
ALTER TABLE assento ADD COLUMN IF NOT EXISTS altura text;
ALTER TABLE modelo_cores ADD COLUMN IF NOT EXISTS tipo_catalogo text;

UPDATE modelo_cores mc
SET tipo_catalogo = 'almofada'
FROM modelos_almofadas m
WHERE mc.id_modelo = m.id
  AND (mc.tipo_catalogo IS NULL OR mc.tipo_catalogo = '');

UPDATE modelo_cores mc
SET tipo_catalogo = 'assento'
FROM modelos_assentos m
WHERE mc.id_modelo = m.id
  AND (mc.tipo_catalogo IS NULL OR mc.tipo_catalogo = '');

DO $$
DECLARE
  r record;
  first_alt text;
BEGIN
  FOR r IN
    SELECT a.id, m.alturas
    FROM assento a
    JOIN modelos_assentos m ON m.id = a.id_modelo
    WHERE a.altura IS NULL OR trim(a.altura) = ''
  LOOP
    first_alt := NULL;
    IF jsonb_typeof(r.alturas) = 'array' AND jsonb_array_length(r.alturas) > 0 THEN
      first_alt := trim(both '"' from (r.alturas->>0));
    END IF;
    IF first_alt IS NOT NULL AND first_alt <> '' THEN
      UPDATE assento SET altura = first_alt WHERE id = r.id;
    END IF;
  END LOOP;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS assento_modelo_altura_idx
  ON assento (id_modelo, altura)
  WHERE altura IS NOT NULL AND altura <> '';

ALTER TABLE assento DROP CONSTRAINT IF EXISTS assento_id_modelo_key;

CREATE INDEX IF NOT EXISTS idx_modelo_cores_tipo_modelo
  ON modelo_cores (tipo_catalogo, id_modelo);

-- === P0 UNIQUE ean (Ago 2026) � ver tamb�m deploy/sql/unique_ean_product_tables.sql ===
CREATE UNIQUE INDEX IF NOT EXISTS uq_almofada_ean ON almofada (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_assento_ean ON assento (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_guarda_chuva_ean ON guarda_chuva (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_oculo_ean ON oculo (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_toalha_mesa_ean ON toalha_mesa (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_avental_ean ON avental (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_luva_ean ON luva (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_pega_ean ON pega (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_pano_cozinha_ean ON pano_cozinha (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_regional_ean ON regional (ean) WHERE ean IS NOT NULL AND btrim(ean) <> '';
