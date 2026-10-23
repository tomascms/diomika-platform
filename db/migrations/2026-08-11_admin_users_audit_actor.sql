-- Sessão admin local: coluna actor na auditoria
ALTER TABLE admin_audit_log ADD COLUMN IF NOT EXISTS actor TEXT;

CREATE INDEX IF NOT EXISTS idx_admin_audit_actor ON admin_audit_log (actor, created_at DESC);
