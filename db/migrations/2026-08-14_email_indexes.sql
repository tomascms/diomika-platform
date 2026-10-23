-- Índices email (retenção / privacy erase / lookups admin)
-- Correr no SQL Editor Supabase se a BD já existir.

CREATE INDEX IF NOT EXISTS idx_contact_messages_email
  ON contact_messages (lower(email));

CREATE INDEX IF NOT EXISTS idx_pedidos_orcamento_email
  ON pedidos_orcamento (lower(email));
