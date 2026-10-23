-- Infraestrutura de produção (v2.3+) — executar no Supabase SQL Editor antes do deploy
-- Ordem: 1) migration_v2_3_catalog.sql (se ainda não aplicada)  2) este ficheiro
-- Alternativa: deploy/supabase_pre_deploy.sql (bundle idempotente)

-- Outbox
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

-- Saga
CREATE TABLE IF NOT EXISTS saga_instances (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    saga_type text NOT NULL,
    status text NOT NULL DEFAULT 'running',
    current_step text,
    context jsonb DEFAULT '{}',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Idempotência
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key text PRIMARY KEY,
    operation text NOT NULL,
    response jsonb NOT NULL,
    created_at timestamptz DEFAULT now(),
    expires_at timestamptz
);
CREATE INDEX IF NOT EXISTS idx_idempotency_expires ON idempotency_keys (expires_at);

-- RLS — catálogo v2.3
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
CREATE POLICY "categories_public_read" ON categories
  FOR SELECT TO anon USING (visibilidade = true);

DROP POLICY IF EXISTS "modelos_public_read" ON modelos_almofadas;
CREATE POLICY "modelos_public_read" ON modelos_almofadas
  FOR SELECT TO anon USING (visibilidade = true);

DROP POLICY IF EXISTS "almofada_public_read" ON almofada;
CREATE POLICY "almofada_public_read" ON almofada
  FOR SELECT TO anon USING (visibilidade = true);

DROP POLICY IF EXISTS "modelo_cores_public_read" ON modelo_cores;
CREATE POLICY "modelo_cores_public_read" ON modelo_cores
  FOR SELECT TO anon USING (visibilidade = true);

DROP POLICY IF EXISTS "pedidos_orcamento_deny_anon" ON pedidos_orcamento;
CREATE POLICY "pedidos_orcamento_deny_anon" ON pedidos_orcamento FOR ALL TO anon USING (false);

DROP POLICY IF EXISTS "encomendas_internas_deny_anon" ON encomendas_internas;
CREATE POLICY "encomendas_internas_deny_anon" ON encomendas_internas FOR ALL TO anon USING (false);

DROP POLICY IF EXISTS "contact_public_insert" ON contact_messages;
CREATE POLICY "contact_deny_anon_insert" ON contact_messages
  FOR INSERT TO anon WITH CHECK (false);

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

-- Storage
DROP POLICY IF EXISTS "product_images_public_read" ON storage.objects;
CREATE POLICY "product_images_public_read" ON storage.objects
  FOR SELECT TO anon
  USING (bucket_id = 'product-images');

DROP POLICY IF EXISTS "product_images_no_anon_write" ON storage.objects;
CREATE POLICY "product_images_no_anon_write" ON storage.objects
  FOR INSERT TO anon WITH CHECK (false);

DROP POLICY IF EXISTS "product_images_no_anon_update" ON storage.objects;
CREATE POLICY "product_images_no_anon_update" ON storage.objects
  FOR UPDATE TO anon USING (false);

DROP POLICY IF EXISTS "product_images_no_anon_delete" ON storage.objects;
CREATE POLICY "product_images_no_anon_delete" ON storage.objects
  FOR DELETE TO anon USING (false);
