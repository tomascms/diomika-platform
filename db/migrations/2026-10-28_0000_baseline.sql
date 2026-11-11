-- ============================================================================
-- Baseline do esquema `public` de produção (auditoria BD-03)
-- ============================================================================
-- Origem: `pg_restore --schema-only` de deploy/backups/pre-drop-legacy-20261021.dump (pg_dump 17.6 da
-- produção a 2026-10-21 23:55), sem as 36 tabelas legacy_* e sem dados. O ficheiro foi gerado lendo o
-- índice (TOC) do dump com um script e copiando o DDL de cada objecto tal como o pg_dump o escreveu.
--
-- Para quê: criar uma base nova (staging, ensaio de recuperação) com
--     baseline + migrações seguintes, por ordem do nome do ficheiro.
-- Em produção NÃO faz nada: o bloco só corre se `public.categories` ainda não existir. É seguro,
-- por isso, aplicá-lo por engano ou voltar a aplicá-lo.
--
-- Não inclui (a produção tem-nos fora do esquema `public`):
--   * o event trigger `ensure_rls` (a Supabase cria-o em cada projecto; a função rls_auto_enable() vem aqui);
--   * os buckets e políticas do Storage: ver o fim deste ficheiro.
-- As migrações de 2026-08-11 a 2026-10-22 estão aqui dentro (os ficheiros antigos estão no histórico do git).
-- ============================================================================

DO $baseline$
BEGIN
  IF to_regclass('public.categories') IS NOT NULL THEN
    RAISE NOTICE 'baseline: public.categories já existe; nada a fazer.';
    RETURN;
  END IF;

  EXECUTE $sql$
CREATE FUNCTION public.diomika_set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO ''
    AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE FUNCTION public.diomika_variant_inherit_tipo() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  SELECT tipo_catalogo INTO NEW.tipo_catalogo
  FROM product_models WHERE id = NEW.id_modelo;
  RETURN NEW;
END
$$;

CREATE FUNCTION public.rls_auto_enable() RETURNS event_trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'pg_catalog'
    AS $$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN
    SELECT *
    FROM pg_event_trigger_ddl_commands()
    WHERE command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      AND object_type IN ('table','partitioned table')
  LOOP
     IF cmd.schema_name IS NOT NULL AND cmd.schema_name IN ('public') AND cmd.schema_name NOT IN ('pg_catalog','information_schema') AND cmd.schema_name NOT LIKE 'pg_toast%' AND cmd.schema_name NOT LIKE 'pg_temp%' THEN
      BEGIN
        EXECUTE format('alter table if exists %s enable row level security', cmd.object_identity);
        RAISE LOG 'rls_auto_enable: enabled RLS on %', cmd.object_identity;
      EXCEPTION
        WHEN OTHERS THEN
          RAISE LOG 'rls_auto_enable: failed to enable RLS on %', cmd.object_identity;
      END;
     ELSE
        RAISE LOG 'rls_auto_enable: skip % (either system schema or not in enforced list: %.)', cmd.object_identity, cmd.schema_name;
     END IF;
  END LOOP;
END;
$$;

CREATE TABLE public.admin_audit_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    action text NOT NULL,
    resource text NOT NULL,
    resource_id text,
    role text DEFAULT 'admin'::text NOT NULL,
    request_id text,
    client_ip text,
    detail jsonb DEFAULT '{}'::jsonb NOT NULL,
    actor text
);

CREATE TABLE public.product_models (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    id_categoria uuid NOT NULL,
    tipo_catalogo text NOT NULL,
    nome text NOT NULL,
    slug text DEFAULT ''::text,
    descricao text DEFAULT ''::text,
    attributes jsonb DEFAULT '{}'::jsonb NOT NULL,
    visibilidade boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT ck_product_models_attributes_object CHECK ((jsonb_typeof(attributes) = 'object'::text)),
    CONSTRAINT ck_product_models_tipo_slug CHECK ((tipo_catalogo ~ '^[a-z][a-z0-9_]*$'::text))
);

CREATE TABLE public.product_variants (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    id_modelo uuid NOT NULL,
    tipo_catalogo text NOT NULL,
    ean text NOT NULL,
    barcode_url text,
    attributes jsonb DEFAULT '{}'::jsonb NOT NULL,
    visibilidade boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT ck_product_variants_attributes_object CHECK ((jsonb_typeof(attributes) = 'object'::text)),
    CONSTRAINT ck_product_variants_ean13 CHECK ((ean ~ '^[0-9]{13}$'::text)),
    CONSTRAINT ck_product_variants_tipo_slug CHECK ((tipo_catalogo ~ '^[a-z][a-z0-9_]*$'::text))
);

CREATE VIEW public.catalog_ean_lookup WITH (security_invoker='true') AS
 SELECT v.tipo_catalogo AS tipo,
    v.id AS product_id,
    v.ean,
    v.id_modelo,
    v.visibilidade AS product_visivel,
    m.visibilidade AS model_visivel
   FROM (public.product_variants v
     JOIN public.product_models m ON ((m.id = v.id_modelo)))
  WHERE ((v.ean IS NOT NULL) AND (btrim(v.ean) <> ''::text));

CREATE TABLE public.categories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    nome text NOT NULL,
    slug text NOT NULL,
    imagem text NOT NULL,
    visibilidade boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    carrinho_step integer DEFAULT 6,
    carrinho_min integer DEFAULT 6,
    tipo_catalogo text DEFAULT 'almofada'::text NOT NULL,
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT categories_carrinho_min_check CHECK (((carrinho_min IS NULL) OR (carrinho_min > 0))),
    CONSTRAINT categories_carrinho_step_check CHECK (((carrinho_step IS NULL) OR (carrinho_step > 0)))
);

CREATE TABLE public.contact_messages (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    nome text NOT NULL,
    email text NOT NULL,
    contacto text,
    assunto text,
    mensagem text,
    lida boolean DEFAULT false,
    status text DEFAULT 'Nova'::text,
    visibilidade boolean DEFAULT true,
    last_sender text,
    updated_at timestamp with time zone DEFAULT now()
);

ALTER TABLE ONLY public.contact_messages REPLICA IDENTITY FULL;

COMMENT ON TABLE public.contact_messages IS 'Armazena cada mensagem submetida através do formulário de contacto do site.';

CREATE TABLE public.encomendas_internas (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    referencia_cliente text NOT NULL,
    observacoes text,
    linhas jsonb DEFAULT '[]'::jsonb NOT NULL,
    visibilidade boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE public.idempotency_keys (
    key text NOT NULL,
    operation text NOT NULL,
    response jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone
);

CREATE TABLE public.message_history (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    message_id uuid,
    sender_email text,
    body text,
    created_at timestamp with time zone DEFAULT now()
);

ALTER TABLE ONLY public.message_history REPLICA IDENTITY FULL;

COMMENT ON TABLE public.message_history IS 'Regista cada resposta trocada (do backoffice ou do cliente), formando o histórico da conversa.';

CREATE TABLE public.outbox_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    event_type text NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    max_attempts integer DEFAULT 5 NOT NULL,
    next_retry_at timestamp with time zone DEFAULT now(),
    last_error text,
    created_at timestamp with time zone DEFAULT now(),
    claimed_by text,
    claimed_at timestamp with time zone
);

CREATE TABLE public.pedidos_orcamento (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    nome text NOT NULL,
    email text NOT NULL,
    contacto text,
    empresa text,
    observacoes text,
    linhas jsonb DEFAULT '[]'::jsonb NOT NULL,
    lida boolean DEFAULT false,
    visibilidade boolean DEFAULT true,
    status text DEFAULT 'Nova'::text,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE public.product_model_colors (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    id_modelo uuid NOT NULL,
    numero integer NOT NULL,
    nome text DEFAULT ''::text,
    imagem text DEFAULT ''::text NOT NULL,
    visibilidade boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE public.saga_instances (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    saga_type text NOT NULL,
    status text DEFAULT 'running'::text NOT NULL,
    current_step text,
    context jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

ALTER TABLE ONLY public.admin_audit_log
    ADD CONSTRAINT admin_audit_log_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_slug_key UNIQUE (slug);

ALTER TABLE ONLY public.contact_messages
    ADD CONSTRAINT contact_messages_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.encomendas_internas
    ADD CONSTRAINT encomendas_internas_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT idempotency_keys_pkey PRIMARY KEY (key);

ALTER TABLE ONLY public.message_history
    ADD CONSTRAINT message_history_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.outbox_events
    ADD CONSTRAINT outbox_events_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.pedidos_orcamento
    ADD CONSTRAINT pedidos_orcamento_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.product_model_colors
    ADD CONSTRAINT product_model_colors_id_modelo_numero_key UNIQUE (id_modelo, numero);

ALTER TABLE ONLY public.product_model_colors
    ADD CONSTRAINT product_model_colors_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.product_models
    ADD CONSTRAINT product_models_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.product_variants
    ADD CONSTRAINT product_variants_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.saga_instances
    ADD CONSTRAINT saga_instances_pkey PRIMARY KEY (id);

CREATE INDEX idx_admin_audit_actor ON public.admin_audit_log USING btree (actor, created_at DESC);

CREATE INDEX idx_admin_audit_created ON public.admin_audit_log USING btree (created_at DESC);

CREATE INDEX idx_admin_audit_resource ON public.admin_audit_log USING btree (resource, created_at DESC);

CREATE INDEX idx_categories_slug ON public.categories USING btree (slug);

CREATE INDEX idx_categories_tipo ON public.categories USING btree (tipo_catalogo);

CREATE INDEX idx_categories_visible_tipo ON public.categories USING btree (tipo_catalogo) WHERE (visibilidade = true);

CREATE INDEX idx_contact_messages_created ON public.contact_messages USING btree (created_at DESC);

CREATE INDEX idx_contact_messages_email ON public.contact_messages USING btree (lower(email));

CREATE INDEX idx_encomendas_created ON public.encomendas_internas USING btree (created_at DESC);

CREATE INDEX idx_idempotency_expires ON public.idempotency_keys USING btree (expires_at);

CREATE INDEX idx_message_history_message_id ON public.message_history USING btree (message_id);

CREATE INDEX idx_outbox_pending ON public.outbox_events USING btree (status, next_retry_at);

CREATE INDEX idx_outbox_processing ON public.outbox_events USING btree (status, claimed_at) WHERE (status = 'processing'::text);

CREATE INDEX idx_pedidos_orcamento_created ON public.pedidos_orcamento USING btree (created_at DESC);

CREATE INDEX idx_pedidos_orcamento_email ON public.pedidos_orcamento USING btree (lower(email));

CREATE INDEX idx_product_model_colors_created ON public.product_model_colors USING btree (created_at DESC);

CREATE INDEX idx_product_model_colors_modelo ON public.product_model_colors USING btree (id_modelo);

CREATE INDEX idx_product_models_attributes ON public.product_models USING gin (attributes);

CREATE INDEX idx_product_models_cat_vis_created ON public.product_models USING btree (id_categoria, visibilidade, created_at DESC);

CREATE INDEX idx_product_models_categoria ON public.product_models USING btree (id_categoria);

CREATE INDEX idx_product_models_slug ON public.product_models USING btree (slug);

CREATE INDEX idx_product_models_tipo ON public.product_models USING btree (tipo_catalogo);

CREATE INDEX idx_product_models_visible ON public.product_models USING btree (id_categoria, created_at DESC) WHERE (visibilidade = true);

CREATE INDEX idx_product_variants_attributes ON public.product_variants USING gin (attributes);

CREATE INDEX idx_product_variants_created ON public.product_variants USING btree (created_at DESC);

CREATE INDEX idx_product_variants_modelo ON public.product_variants USING btree (id_modelo);

CREATE INDEX idx_product_variants_modelo_vis ON public.product_variants USING btree (id_modelo, visibilidade);

CREATE INDEX idx_product_variants_tipo ON public.product_variants USING btree (tipo_catalogo);

CREATE INDEX idx_saga_running ON public.saga_instances USING btree (updated_at) WHERE (status = 'running'::text);

CREATE UNIQUE INDEX uq_product_variants_ean ON public.product_variants USING btree (ean) WHERE ((ean IS NOT NULL) AND (btrim(ean) <> ''::text));

CREATE TRIGGER trg_categories_updated_at BEFORE UPDATE ON public.categories FOR EACH ROW EXECUTE FUNCTION public.diomika_set_updated_at();

CREATE TRIGGER trg_product_models_updated_at BEFORE UPDATE ON public.product_models FOR EACH ROW EXECUTE FUNCTION public.diomika_set_updated_at();

CREATE TRIGGER trg_product_variants_inherit_tipo BEFORE INSERT OR UPDATE OF id_modelo, tipo_catalogo ON public.product_variants FOR EACH ROW EXECUTE FUNCTION public.diomika_variant_inherit_tipo();

CREATE TRIGGER trg_product_variants_updated_at BEFORE UPDATE ON public.product_variants FOR EACH ROW EXECUTE FUNCTION public.diomika_set_updated_at();

ALTER TABLE ONLY public.message_history
    ADD CONSTRAINT message_history_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.contact_messages(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.product_model_colors
    ADD CONSTRAINT product_model_colors_id_modelo_fkey FOREIGN KEY (id_modelo) REFERENCES public.product_models(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.product_models
    ADD CONSTRAINT product_models_id_categoria_fkey FOREIGN KEY (id_categoria) REFERENCES public.categories(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.product_variants
    ADD CONSTRAINT product_variants_id_modelo_fkey FOREIGN KEY (id_modelo) REFERENCES public.product_models(id) ON DELETE CASCADE;

CREATE POLICY admin_audit_deny_anon ON public.admin_audit_log TO anon USING (false);

ALTER TABLE public.admin_audit_log ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.categories ENABLE ROW LEVEL SECURITY;

CREATE POLICY categories_public_read ON public.categories FOR SELECT TO anon USING ((visibilidade = true));

CREATE POLICY contact_deny_anon_insert ON public.contact_messages FOR INSERT TO anon WITH CHECK (false);

CREATE POLICY contact_deny_anon_select ON public.contact_messages FOR SELECT TO anon USING (false);

ALTER TABLE public.contact_messages ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.encomendas_internas ENABLE ROW LEVEL SECURITY;

CREATE POLICY encomendas_internas_deny_anon ON public.encomendas_internas TO anon USING (false);

CREATE POLICY history_deny_anon ON public.message_history TO anon USING (false);

CREATE POLICY idempotency_deny_anon ON public.idempotency_keys TO anon USING (false);

ALTER TABLE public.idempotency_keys ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.message_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY outbox_deny_anon ON public.outbox_events TO anon USING (false);

ALTER TABLE public.outbox_events ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.pedidos_orcamento ENABLE ROW LEVEL SECURITY;

CREATE POLICY pedidos_orcamento_deny_anon ON public.pedidos_orcamento TO anon USING (false);

ALTER TABLE public.product_model_colors ENABLE ROW LEVEL SECURITY;

CREATE POLICY product_model_colors_deny_anon_delete ON public.product_model_colors FOR DELETE TO anon USING (false);

CREATE POLICY product_model_colors_deny_anon_update ON public.product_model_colors FOR UPDATE TO anon USING (false) WITH CHECK (false);

CREATE POLICY product_model_colors_deny_anon_write ON public.product_model_colors FOR INSERT TO anon WITH CHECK (false);

CREATE POLICY product_model_colors_public_read ON public.product_model_colors FOR SELECT TO anon USING ((visibilidade = true));

ALTER TABLE public.product_models ENABLE ROW LEVEL SECURITY;

CREATE POLICY product_models_deny_anon_delete ON public.product_models FOR DELETE TO anon USING (false);

CREATE POLICY product_models_deny_anon_update ON public.product_models FOR UPDATE TO anon USING (false) WITH CHECK (false);

CREATE POLICY product_models_deny_anon_write ON public.product_models FOR INSERT TO anon WITH CHECK (false);

CREATE POLICY product_models_public_read ON public.product_models FOR SELECT TO anon USING ((visibilidade = true));

ALTER TABLE public.product_variants ENABLE ROW LEVEL SECURITY;

CREATE POLICY product_variants_deny_anon_delete ON public.product_variants FOR DELETE TO anon USING (false);

CREATE POLICY product_variants_deny_anon_update ON public.product_variants FOR UPDATE TO anon USING (false) WITH CHECK (false);

CREATE POLICY product_variants_deny_anon_write ON public.product_variants FOR INSERT TO anon WITH CHECK (false);

CREATE POLICY product_variants_public_read ON public.product_variants FOR SELECT TO anon USING ((visibilidade = true));

CREATE POLICY saga_deny_anon ON public.saga_instances TO anon USING (false);

ALTER TABLE public.saga_instances ENABLE ROW LEVEL SECURITY;

  $sql$;

  -- 2026-10-21_function_search_path.sql (aplicada depois do dump).
  ALTER FUNCTION public.diomika_variant_inherit_tipo() SET search_path = public, pg_temp;
END
$baseline$;

-- ----------------------------------------------------------------------------
-- Storage (reconstruído do relatório de auditoria BD-07; não vem do dump, que só tem `public`).
-- Idempotente. A migração 2026-11-02_database_hardening.sql ajusta limites e retira a listagem pública.
-- ----------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public)
VALUES ('product-images', 'product-images', true)
ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS product_images_public_read ON storage.objects;
CREATE POLICY product_images_public_read ON storage.objects
  FOR SELECT TO anon USING (bucket_id = 'product-images');
