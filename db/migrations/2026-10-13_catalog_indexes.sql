-- Índices para otimizar queries de catálogo
-- Correr no Supabase SQL Editor se a BD já existir

-- Categories: lookups por slug, tipo_catalogo, visibilidade
CREATE INDEX IF NOT EXISTS idx_categories_slug
  ON categories (slug);

CREATE INDEX IF NOT EXISTS idx_categories_tipo_catalogo
  ON categories (tipo_catalogo);

CREATE INDEX IF NOT EXISTS idx_categories_visible
  ON categories (visibilidade);

-- Product models: queries frequentes de catálogo (já existem, replicados para clareza)
CREATE INDEX IF NOT EXISTS idx_product_models_cat_visible
  ON product_models (id_categoria, visibilidade);

-- Contact/Messages: timestamp para ordenaç ão e paginação
CREATE INDEX IF NOT EXISTS idx_contact_messages_created
  ON contact_messages (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pedidos_orcamento_created
  ON pedidos_orcamento (created_at DESC);

-- Outbox/Saga: polling eficiente
CREATE INDEX IF NOT EXISTS idx_outbox_status_retry
  ON outbox_events (status, next_retry_at);

CREATE INDEX IF NOT EXISTS idx_saga_instances_status
  ON saga_instances (status);
